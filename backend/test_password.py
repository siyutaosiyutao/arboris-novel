#!/usr/bin/env python3
"""测试密码验证"""
import bcrypt

# 从数据库中获取的哈希
db_hash = "$2b$12$NubNorp/r0qBmfJi31JCwOS44HjS/fYuKcEFGsvQnOIpPH0S66lJa"

# 测试密码
test_passwords = ["admin123", "admin", "Admin123", "password"]

print("测试密码验证:")
print(f"数据库哈希: {db_hash}")
print(f"哈希长度: {len(db_hash)}")
print()

for pwd in test_passwords:
    try:
        result = bcrypt.checkpw(pwd.encode('utf-8'), db_hash.encode('utf-8'))
        print(f"密码 '{pwd}': {'✓ 正确' if result else '✗ 错误'}")
    except Exception as e:
        print(f"密码 '{pwd}': 错误 - {e}")

print("\n生成新的密码哈希:")
new_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
print(f"admin123 的新哈希: {new_hash.decode('utf-8')}")
result = bcrypt.checkpw("admin123".encode('utf-8'), new_hash)
print(f"验证新哈希: {'✓ 正确' if result else '✗ 错误'}")
