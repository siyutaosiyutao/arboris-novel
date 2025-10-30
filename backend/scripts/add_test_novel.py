"""
添加测试小说数据的脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.models.novel import NovelProject, NovelBlueprint, Volume, Chapter, ChapterVersion
from app.models.user import User
from datetime import datetime


async def add_test_novel():
    """添加测试小说数据"""
    async with AsyncSessionLocal() as session:
        # 获取管理员用户
        result = await session.execute(
            text("SELECT id FROM users WHERE username = 'admin'")
        )
        user_id = result.scalar_one()
        
        # 创建小说项目
        project = NovelProject(
            id="test-novel-001",
            user_id=user_id,
            title="修仙传奇",
            initial_prompt="创作一部玄幻修仙小说,讲述一个普通少年的修仙之路",
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(project)
        
        # 创建蓝图
        blueprint = NovelBlueprint(
            project_id=project.id,
            title="修仙传奇",
            genre="玄幻修仙",
            target_audience="18-35岁男性读者",
            style="热血爽文",
            tone="轻松愉快",
            one_sentence_summary="一个普通少年意外获得上古传承,踏上修仙之路的故事",
            full_synopsis="""
林风是一个普通的山村少年,在一次采药时意外跌落山崖,发现了上古修仙者的洞府,获得了《太玄真经》传承。
凭借这份传承,林风拜入天剑宗,开始了修仙之路。在宗门中,他结识了好友张浩,也遭遇了敌对势力的挑战。
通过不断努力修炼,林风逐渐崭露头角,在宗门大比中展现出惊人的天赋...
            """.strip(),
            world_setting={
                "description": "修仙世界,分为凡人界、修真界、仙界",
                "power_system": "炼气、筑基、金丹、元婴、化神、合体、渡劫、大乘",
                "factions": ["天剑宗", "玄天门", "万妖谷"]
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(blueprint)
        
        # 创建第一卷
        volume1 = Volume(
            project_id=project.id,
            volume_number=1,
            title="初入修仙界",
            description="林风踏上修仙之路的开始",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(volume1)
        await session.flush()  # 获取 volume1.id
        
        # 创建第一章
        chapter1 = Chapter(
            project_id=project.id,
            volume_id=volume1.id,
            chapter_number=1,
            real_summary="林风在山中采药时意外跌落山崖,发现一个神秘洞府,获得上古修仙传承。",
            status="completed",
            word_count=3500,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(chapter1)
        await session.flush()
        
        # 创建第一章内容
        chapter1_content = """第一章 山崖奇遇

青云山脉,连绵千里,云雾缭绕。

十六岁的林风背着竹篓,在山间小路上艰难前行。他是青云村的普通少年,今天进山是为了采集草药,好换些银两补贴家用。

"娘的病越来越重了,必须多采些药材才行。"林风心中暗想,脚步不由加快了几分。

突然,脚下一滑!

"啊!"林风惊呼一声,身体失去平衡,向山崖边缘滑去。

他拼命想要抓住什么,但周围只有光滑的岩石。眼看就要跌落万丈深渊,林风心中涌起绝望。

"难道我就要这样死了吗?娘还在等我回去..."

就在这时,一股神秘的力量突然出现,托住了他的身体。林风只觉得眼前一黑,便失去了知觉。

不知过了多久,林风悠悠转醒。

"这是...哪里?"

他发现自己躺在一个石室中,四周墙壁上刻满了奇异的符文,散发着淡淡的光芒。石室中央,有一个石台,上面放着一枚古朴的玉简。

林风小心翼翼地走过去,拿起玉简。

刹那间,无数信息涌入他的脑海!

"《太玄真经》...这是修仙功法!"林风震惊不已。

原来,这个洞府是一位上古大能留下的传承之地。那位大能在此留下了毕生所学,等待有缘人继承。

"修仙...原来世上真的有修仙者!"林风激动得浑身颤抖。

他立刻盘膝坐下,按照《太玄真经》的心法开始修炼。

一股股灵气从天地间汇聚而来,涌入林风的身体。他感觉到前所未有的舒畅,体内仿佛有一股暖流在流动。

"这就是灵气吗?太神奇了!"

林风沉浸在修炼之中,忘记了时间的流逝。

当他再次睁开眼睛时,已经是三天后。

"我...我突破了!炼气一层!"林风惊喜地发现,自己已经踏入了修仙的门槛。

他站起身来,感觉浑身充满了力量。随手一拳打出,竟然在空气中发出"呼呼"的破空声。

"有了这份传承,我一定能治好娘的病,让家人过上好日子!"林风心中充满了希望。

他收拾好洞府中的宝物,沿着一条隐秘的通道离开了山崖。

当林风回到村子时,已经是傍晚时分。

"风儿,你可算回来了!娘还以为你出事了呢。"母亲看到他,眼中满是担忧。

"娘,我没事。而且,我还有一个天大的好消息要告诉您!"林风笑着说道。

他知道,自己的命运,从今天开始,将彻底改变。

修仙之路,就此开启!

(本章完)"""
        
        version1 = ChapterVersion(
            chapter_id=chapter1.id,
            version_label="初稿",
            provider="manual",
            content=chapter1_content,
            created_at=datetime.now()
        )
        session.add(version1)
        await session.flush()
        
        # 设置选中的版本
        chapter1.selected_version_id = version1.id
        
        # 创建第二章
        chapter2 = Chapter(
            project_id=project.id,
            volume_id=volume1.id,
            chapter_number=2,
            real_summary="林风决定前往天剑宗拜师学艺,在路上遇到了同样前往宗门的少年张浩,两人结伴而行。",
            status="completed",
            word_count=3200,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(chapter2)
        await session.flush()
        
        chapter2_content = """第二章 踏上征途

获得传承后的第三天,林风做出了一个重要决定。

"娘,我要去天剑宗拜师学艺。"林风郑重地说道。

母亲愣了一下,随即露出欣慰的笑容:"风儿长大了,有自己的想法了。娘支持你,但你要记住,无论走到哪里,都要做一个正直的人。"

"娘,您放心,我一定会让您过上好日子的!"林风眼眶有些湿润。

第二天清晨,林风背起简单的行囊,踏上了前往天剑宗的道路。

天剑宗位于千里之外的天剑峰,是修真界的顶尖宗门之一。每年都会招收新弟子,但要求极为严格。

林风走了三天,来到了一个小镇。

"这位小兄弟,看你也是要去天剑宗的吧?"一个声音从身后传来。

林风转身,看到一个和自己年纪相仿的少年,身穿青衫,背着长剑,一脸笑意。

"是的,在下林风,敢问兄台..."

"我叫张浩,也是去天剑宗拜师的。既然同路,不如结伴而行?"张浩爽朗地说道。

"好啊!"林风欣然同意。

两人一路同行,很快就成了朋友。

"林兄,你修炼多久了?"张浩好奇地问道。

"我...才刚开始修炼不久。"林风如实说道,但没有透露获得传承的事。

"哈哈,我也是!我家世代习武,但直到半年前才接触到修仙功法。"张浩说道,"不过能不能通过天剑宗的考核,还真不好说。"

"只要努力,一定可以的。"林风鼓励道。

就在这时,前方传来一阵喧哗声。

"发生什么事了?"两人加快脚步,来到人群前。

只见一个衣衫褴褛的老者倒在地上,周围围着一群人,但没有人上前帮忙。

"这老头是个疯子,别管他!"有人说道。

林风皱了皱眉,走上前去:"老人家,您没事吧?"

老者抬起头,浑浊的眼睛中闪过一丝精光:"小伙子,有心了。能扶老夫起来吗?"

林风毫不犹豫地伸出手,将老者扶了起来。

"多谢,多谢。"老者拍了拍身上的尘土,突然笑道,"小伙子,你有一颗善良的心,将来必成大器。"

说完,老者从怀中掏出一块玉佩,塞到林风手中:"这个送给你,算是报答。"

还没等林风反应过来,老者已经转身离去,很快消失在人群中。

"林兄,让我看看那玉佩。"张浩凑过来。

林风打开手掌,只见玉佩温润如玉,上面刻着一个"剑"字。

"这...这是天剑令!"张浩惊呼道,"有了这个,可以直接进入天剑宗,不用参加考核!"

林风也愣住了。

那个老者,究竟是什么人?

(本章完)"""
        
        version2 = ChapterVersion(
            chapter_id=chapter2.id,
            version_label="初稿",
            provider="manual",
            content=chapter2_content,
            created_at=datetime.now()
        )
        session.add(version2)
        await session.flush()
        
        chapter2.selected_version_id = version2.id
        
        # 创建第三章
        chapter3 = Chapter(
            project_id=project.id,
            volume_id=volume1.id,
            chapter_number=3,
            real_summary="林风和张浩抵达天剑宗,参加入门考核。林风凭借天剑令直接入门,而张浩也通过了考核。",
            status="completed",
            word_count=3400,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(chapter3)
        await session.flush()
        
        chapter3_content = """第三章 天剑宗

又过了五天,林风和张浩终于来到了天剑峰下。

抬头望去,只见一座巍峨的山峰直插云霄,山腰处云雾缭绕,隐约可见宫殿楼阁,仙气飘飘。

"这就是天剑宗...好壮观!"张浩感叹道。

山脚下,已经聚集了数百名前来拜师的少年。

"诸位,天剑宗三年一次的招收弟子大会即将开始!"一个中年修士飞身而至,声音洪亮,"本次考核分为三关:测试灵根、实战比试、心性考验。只有通过全部考核的人,才能成为天剑宗的外门弟子!"

众人议论纷纷。

"林兄,你有天剑令,可以直接入门,真是羡慕啊。"张浩说道。

"张兄,以你的实力,一定能通过考核的。"林风鼓励道。

考核很快开始。

第一关,测试灵根。

一块巨大的测灵石被搬了出来,只要将手放在上面,就能测出灵根的属性和品质。

"单灵根者,为天才!双灵根者,为良才!三灵根者,为普通!四灵根以上者,不予录取!"中年修士宣布道。

张浩走上前,将手放在测灵石上。

石头发出淡淡的光芒,显示出"金木双灵根"的字样。

"双灵根,不错!"中年修士点头,"通过第一关。"

张浩松了口气,退到一旁。

很快轮到林风。

他走上前,将手放在测灵石上。

刹那间,测灵石爆发出耀眼的光芒!

"这是...五行灵根!"中年修士震惊道,"而且每一种属性都极为纯净,这是...天灵根!"

周围一片哗然。

天灵根,万中无一的修仙天才!

"好,好!"中年修士激动不已,"你叫什么名字?"

"林风。"

"林风,很好!你不仅通过了第一关,而且可以直接成为内门弟子!"

林风还没来得及高兴,突然想起了天剑令。

"前辈,晚辈有天剑令,本可以直接入门,但晚辈想和朋友一起参加考核。"林风说道。

"哦?让我看看。"中年修士接过天剑令,脸色一变,"这是...掌门的令牌!你从哪里得到的?"

林风将遇到老者的事情说了一遍。

中年修士沉思片刻,笑道:"原来如此。那老者应该就是我们的掌门。他云游在外,经常化身考验有缘人。你能得到这块令牌,说明你通过了掌门的考验。"

"不过,既然你想参加考核,那就继续吧。以你的天赋,通过考核轻而易举。"

接下来的两关,林风和张浩都顺利通过。

当夕阳西下时,数百名考生中,只有三十人通过了全部考核。

"恭喜你们,从今天起,你们就是天剑宗的弟子了!"中年修士宣布道。

林风和张浩对视一眼,都露出了笑容。

修仙之路,正式开始!

(本章完)"""
        
        version3 = ChapterVersion(
            chapter_id=chapter3.id,
            version_label="初稿",
            provider="manual",
            content=chapter3_content,
            created_at=datetime.now()
        )
        session.add(version3)
        await session.flush()
        
        chapter3.selected_version_id = version3.id
        
        # 提交所有更改
        await session.commit()
        
        print("✅ 测试小说数据添加成功!")
        print(f"项目ID: {project.id}")
        print(f"项目标题: {project.title}")
        print(f"分卷: {volume1.title}")
        print(f"章节数: 3")


if __name__ == "__main__":
    asyncio.run(add_test_novel())

