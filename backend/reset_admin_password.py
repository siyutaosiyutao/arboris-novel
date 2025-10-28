#!/usr/bin/env python3
"""重置管理员密码"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import hash_password


async def reset_admin_password():
    """重置管理员密码为 admin123"""
    async with AsyncSessionLocal() as db:
        # 查找管理员
        result = await db.execute(
            select(User).where(User.username == "admin")
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("❌ 管理员账号不存在")
            return
        
        # 重置密码
        new_password = "admin123"
        hashed_password = hash_password(new_password)
        
        await db.execute(
            update(User)
            .where(User.id == admin.id)
            .values(hashed_password=hashed_password)
        )
        await db.commit()
        
        print(f"✅ 管理员密码已重置")
        print(f"用户名: admin")
        print(f"密码: {new_password}")


if __name__ == "__main__":
    asyncio.run(reset_admin_password())

