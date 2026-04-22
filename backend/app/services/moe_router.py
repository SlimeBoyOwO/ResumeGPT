"""Agent Router for MoE Workflow Generation."""

import json
import logging
from collections import defaultdict, deque
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.expert import Expert
from app.models.job_description import JobDescription

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def _get_async_client() -> AsyncOpenAI:
    if not settings.CHAT_API_KEY:
        raise RuntimeError("CHAT_API_KEY is not configured.")
    return AsyncOpenAI(api_key=settings.CHAT_API_KEY, base_url=settings.CHAT_API_BASE_URL)

async def auto_generate_workflow_graph(jd_id: int):
    """
    Automatically select experts and generate a DAG workflow graph for a given JD.
    """
    logger.info(f"Starting MoE Router for JD {jd_id}")
    try:
        async with async_session_factory() as session:
            jd = await session.get(JobDescription, jd_id)
            if not jd:
                logger.error(f"JD {jd_id} not found.")
                return

            if jd.workflow_graph:
                logger.info(f"JD {jd_id} already has a workflow graph.")
                return

            # Fetch all available experts
            result = await session.execute(select(Expert))
            experts = result.scalars().all()
            
            if not experts:
                logger.warning("No experts found in the system. Cannot build MoE flow.")
                return

            expert_info_lines = []
            for ex in experts:
                expert_info_lines.append(f"- 专家 ID: {ex.id}, 名称: {ex.name}, 侧重描述: {ex.description}")
            expert_info = "\n".join(expert_info_lines)

            jd_content = f"岗位名称: {jd.title}\n所属部门: {jd.department or '无'}\n岗位描述与要求:\n{jd.description}"

            system_prompt = """
你是一个高级工作流引擎编排规划专家（MoE Router Agent）。你当前的任务是“自动搭建节点流”。
根据用户提供的【岗位JD信息】和当前系统中可用的【专家列表】，为其挑选最符合要求的审查专家，并生成一个审查工作流（图/DAG）。

要求：
1. 请认真阅读JD要求，从【专家列表】中挑选至少2个，最多5个相关的专家。对于常规的全能专家可以作为综合评估节点。
2. 每一个你选中的专家，都对应图中的一个独立节点（Node）。
3. 如果某些专家评估不依赖其他项，可以让他们作为起点（并行运行）；如果某个综合评估专家必须要参考前置专家的评价，请通过设定边（Edge）让其成为后置节点。
4. 每一个被选取的专家节点，你需要给出一个权重(weight，浮点数)，表示该专家的最终得分占总分的比重。所有选用节点的 weight 之和应等于 1.0。
5. 务必严格遵守并输出 JSON 格式。包含 "nodes" 数组和 "edges" 数组。

生成的 JSON 模板示例（请不要改变内部键名的含义）：
{
  "nodes": [
    {
      "id": "node_1",
      "label": "技术能力专家", // 专家的真实名称
      "data": {
        "expert_id": 1, // 专家在数据库中的真实ID
        "weight": 0.6
      }
    },
    {
      "id": "node_2",
      "label": "HR综合评估专家",
      "data": {
        "expert_id": 4,
        "weight": 0.4
      }
    }
  ],
  "edges": [
    {
      "source": "node_1", // 必须匹配 nodes 中的 id
      "target": "node_2"  // 只有存在先后依赖或者流程汇聚时才加边。如果需要独立并行给分，也可以不需要边。
    }
  ]
}
"""

            user_prompt = f"【系统中可用的专家列表】:\n{expert_info}\n\n【给定的岗位JD信息】:\n{jd_content}\n\n请评估并设计其 MoE Agent 工作流逻辑流，输出 JSON："

            client = _get_async_client()
            
            response = await client.chat.completions.create(
                model=settings.CHAT_API_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            
            res_text = response.choices[0].message.content or "{}"
            workflow_graph = json.loads(res_text)

            # Post-process: add type and position for frontend VueFlow rendering
            workflow_graph = _add_layout_to_graph(workflow_graph)

            # Update the JD with the new workflow graph
            jd.workflow_graph = workflow_graph
            session.add(jd)
            await session.commit()
            
            # To notify any background execution waiting for auto_pending, its status changes essentially.
            # Here we just save it. The system picks it up correctly based on standard flows.
            
            logger.info(f"Successfully generated workflow graph for JD {jd_id}: {workflow_graph}")
            
    except Exception as e:
        logger.error(f"Failed to auto-generate MoE workflow for JD {jd_id}: {e}", exc_info=True)


def _add_layout_to_graph(graph: dict) -> dict:
    """Add type='custom' and auto-layout positions to AI-generated nodes."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    node_ids = {n["id"] for n in nodes}
    adj: dict[str, list[str]] = defaultdict(list)
    in_deg: dict[str, int] = {nid: 0 for nid in node_ids}

    for e in edges:
        src, tgt = e.get("source"), e.get("target")
        if src in node_ids and tgt in node_ids:
            adj[src].append(tgt)
            in_deg[tgt] += 1

    # BFS topological layering
    queue = deque()
    layer_map: dict[str, int] = {}
    for nid, deg in in_deg.items():
        if deg == 0:
            queue.append(nid)
            layer_map[nid] = 0

    while queue:
        nid = queue.popleft()
        for child in adj[nid]:
            in_deg[child] -= 1
            layer_map[child] = max(layer_map.get(child, 0), layer_map[nid] + 1)
            if in_deg[child] == 0:
                queue.append(child)

    # Group by layer and assign positions
    layers: dict[int, list[str]] = defaultdict(list)
    for nid, layer in layer_map.items():
        layers[layer].append(nid)

    x_spacing, y_spacing = 300, 150
    node_positions: dict[str, dict] = {}
    for layer_idx in sorted(layers.keys()):
        layer_nodes = layers[layer_idx]
        total_height = (len(layer_nodes) - 1) * y_spacing
        start_y = -total_height / 2
        for i, nid in enumerate(layer_nodes):
            node_positions[nid] = {
                "x": layer_idx * x_spacing + 50,
                "y": start_y + i * y_spacing + 50,
            }

    for n in nodes:
        n["type"] = "custom"
        if "position" not in n:
            n["position"] = node_positions.get(n["id"], {"x": 50, "y": 50})

    return graph
