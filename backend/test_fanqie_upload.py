"""
番茄小说上传功能测试脚本

使用方法：
1. 先运行登录流程保存Cookie：
   python test_fanqie_upload.py login

2. 然后测试上传功能：
   python test_fanqie_upload.py upload <project_id>
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.fanqie_publisher_service import FanqiePublisherService
from app.db.session import async_session_maker


async def test_login():
    """测试手动登录并保存Cookie"""
    print("=" * 60)
    print("番茄小说手动登录测试")
    print("=" * 60)
    
    async with FanqiePublisherService() as publisher:
        result = await publisher.manual_login_and_save_cookies(
            account="default",
            wait_seconds=120  # 等待2分钟
        )
    
    print("\n登录结果:")
    print(result)
    return result


async def test_upload(project_id: str):
    """测试上传小说到番茄小说"""
    print("=" * 60)
    print(f"番茄小说上传测试 - 项目ID: {project_id}")
    print("=" * 60)
    
    async with async_session_maker() as session:
        async with FanqiePublisherService() as publisher:
            result = await publisher.upload_novel_to_fanqie(
                db=session,
                project_id=project_id,
                account="default"
            )
    
    print("\n上传结果:")
    print(f"成功: {result.get('success')}")
    print(f"书籍ID: {result.get('book_id')}")
    print(f"书名: {result.get('book_name')}")
    print(f"分卷数: {result.get('volume_count')}")
    print(f"章节数: {result.get('chapter_count')}")
    
    if not result.get('success'):
        print(f"错误: {result.get('error')}")
    
    # 打印详细的上传结果
    if result.get('upload_results'):
        print("\n章节上传详情:")
        for i, chapter_result in enumerate(result['upload_results'], 1):
            status = "✓" if chapter_result.get('success') else "✗"
            print(f"  {status} 第{chapter_result.get('chapter_number')}章: {chapter_result.get('title')}")
            if not chapter_result.get('success'):
                print(f"    错误: {chapter_result.get('error')}")
    
    return result


async def test_find_book():
    """测试查找书籍功能"""
    print("=" * 60)
    print("测试查找书籍功能")
    print("=" * 60)
    
    book_name = input("请输入要查找的书名: ")
    
    async with FanqiePublisherService() as publisher:
        # 加载Cookie
        await publisher.load_cookies("default")
        
        # 查找书籍
        book_id = await publisher.find_book_by_name(book_name)
        
        if book_id:
            print(f"\n✓ 找到书籍: {book_name}")
            print(f"  书籍ID: {book_id}")
        else:
            print(f"\n✗ 未找到书籍: {book_name}")
    
    return book_id


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python test_fanqie_upload.py login              # 手动登录并保存Cookie")
        print("  python test_fanqie_upload.py upload <project_id> # 上传小说")
        print("  python test_fanqie_upload.py find               # 查找书籍")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "login":
        asyncio.run(test_login())
    elif command == "upload":
        if len(sys.argv) < 3:
            print("错误: 请提供项目ID")
            print("使用方法: python test_fanqie_upload.py upload <project_id>")
            sys.exit(1)
        project_id = sys.argv[2]
        asyncio.run(test_upload(project_id))
    elif command == "find":
        asyncio.run(test_find_book())
    else:
        print(f"未知命令: {command}")
        print("可用命令: login, upload, find")
        sys.exit(1)


if __name__ == "__main__":
    main()

