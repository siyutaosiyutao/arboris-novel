"""番茄小说发布服务测试脚本"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.fanqie_publisher_service import FanqiePublisherService


async def test_publish_single_chapter():
    """测试发布单个章节"""
    
    # 测试数据
    test_chapter = {
        "chapter_number": 2,
        "title": "初入江湖",  # 注意:不要包含"第X章"
        "content": """
        李明睁开眼睛,发现自己躺在一片陌生的草地上。
        
        "这是哪里?"他喃喃自语,努力回忆着之前发生的事情。
        
        记忆中,他正在公司加班,突然一阵眩晕,然后就失去了意识。现在醒来,却发现自己身处一个完全陌生的地方。
        
        周围是茂密的森林,远处传来不知名鸟兽的叫声。天空中挂着两轮太阳,散发着柔和的光芒。
        
        "两个太阳?这不可能!"李明惊呼道。
        
        就在这时,一个穿着古装的老者从林中走出,看到李明后露出惊讶的表情。
        
        "年轻人,你是从哪里来的?"老者问道。
        
        李明不知如何回答,只能如实说道:"我...我也不知道。我只记得我在加班,然后就到这里了。"
        
        老者打量着李明,若有所思地点了点头:"看来你是从外界来的。这里是修仙界,凡人很少能到达这里。"
        
        "修仙界?"李明瞪大了眼睛,"您是说,这里是修仙的世界?"
        
        "没错。"老者微笑道,"既然你能来到这里,说明你与修仙有缘。我叫张三丰,是附近天剑宗的长老。你愿意跟我学习修仙吗?"
        
        李明激动得说不出话来。穿越到修仙世界,这不正是他梦寐以求的吗?
        
        "我愿意!"他毫不犹豫地答道。
        
        就这样,李明开始了他在修仙界的新生活。
        
        张三丰带着李明来到天剑宗,一路上向他介绍着修仙界的基本知识。
        
        "修仙分为九个境界,"张三丰说道,"分别是炼气、筑基、金丹、元婴、化神、炼虚、合体、大乘、渡劫。每个境界又分为初期、中期、后期和圆满四个阶段。"
        
        李明认真地听着,将这些知识牢记在心。
        
        "那么,我现在是什么境界?"他问道。
        
        张三丰摇了摇头:"你现在还是凡人,连炼气期都没有达到。不过不用担心,只要你努力修炼,很快就能突破。"
        
        两人来到天剑宗的山门前,李明抬头望去,只见一座巍峨的山峰耸立在云端,山腰处建有无数宫殿楼阁,气势恢宏。
        
        "这就是天剑宗。"张三丰介绍道,"我们宗门有弟子三千,是修仙界的一流宗门。"
        
        李明心中充满了期待,他知道,自己的修仙之路,从这里开始了。
        """.strip(),
        "volume_name": "初入江湖"  # 可选
    }
    
    async with FanqiePublisherService() as publisher:
        # 1. 初始化浏览器(非无头模式,方便观察)
        print("正在初始化浏览器...")
        
        # 2. 尝试加载Cookie
        print("尝试加载已保存的Cookie...")
        cookie_loaded = await publisher.load_cookies()
        
        if not cookie_loaded:
            print("未找到Cookie,需要手动登录")
            print("请在浏览器中手动登录番茄小说...")
            
            # 打开登录页面
            await publisher.page.goto("https://fanqienovel.com/main/writer/book-manage")
            
            # 等待用户手动登录
            print("等待登录完成...")
            await publisher.page.wait_for_url("**/main/writer/**", timeout=120000)
            
            # 保存Cookie
            await publisher.save_cookies()
            print("Cookie已保存")
        
        # 3. 导航到书籍管理页面
        print("导航到书籍管理页面...")
        book_id = "7566232657483287576"  # 替换为你的书籍ID
        await publisher.navigate_to_book(book_id)
        
        # 4. 发布章节
        print(f"\n开始发布章节: 第{test_chapter['chapter_number']}章 {test_chapter['title']}")
        result = await publisher.publish_chapter(
            chapter_number=test_chapter["chapter_number"],
            chapter_title=test_chapter["title"],
            content=test_chapter["content"],
            volume_name=test_chapter.get("volume_name"),
            run_risk_detection=True,
            auto_correct_errors=True,
            use_ai=False
        )
        
        # 5. 输出结果
        print("\n发布结果:")
        print(f"  成功: {result['success']}")
        if result['success']:
            print(f"  章节号: {result['chapter_number']}")
            print(f"  标题: {result['title']}")
            print(f"  状态: {result['status']}")
        else:
            print(f"  错误: {result.get('error')}")


async def test_batch_publish():
    """测试批量发布章节"""
    
    chapters = [
        {
            "chapter_number": 3,
            "title": "拜师学艺",
            "content": "..." * 500,  # 实际内容
            "volume_name": "初入江湖"
        },
        {
            "chapter_number": 4,
            "title": "初试身手",
            "content": "..." * 500,
            "volume_name": "初入江湖"
        },
    ]
    
    async with FanqiePublisherService() as publisher:
        await publisher.load_cookies()
        await publisher.navigate_to_book("7566232657483287576")
        
        results = await publisher.batch_publish_chapters(
            chapters=chapters,
            interval_seconds=10  # 每章间隔10秒
        )
        
        print(f"\n批量发布完成,成功: {sum(1 for r in results if r['success'])}/{len(results)}")


async def test_create_volume():
    """测试创建分卷"""
    
    async with FanqiePublisherService() as publisher:
        await publisher.load_cookies()
        await publisher.navigate_to_book("7566232657483287576")
        
        result = await publisher.create_volume("初入江湖")
        
        print(f"\n创建分卷结果: {result}")


if __name__ == "__main__":
    # 运行测试
    print("=== 番茄小说发布服务测试 ===\n")
    
    # 选择测试类型
    print("请选择测试类型:")
    print("1. 发布单个章节")
    print("2. 批量发布章节")
    print("3. 创建分卷")
    
    choice = input("\n请输入选项(1-3): ").strip()
    
    if choice == "1":
        asyncio.run(test_publish_single_chapter())
    elif choice == "2":
        asyncio.run(test_batch_publish())
    elif choice == "3":
        asyncio.run(test_create_volume())
    else:
        print("无效选项")

