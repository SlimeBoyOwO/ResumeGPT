"""生成管理员密码哈希"""
import bcrypt

password = "admin123"
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
print(hashed)
