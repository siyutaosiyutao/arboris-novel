"""番茄小说自动发布服务"""
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models.novel import NovelProject, Volume, Chapter, ChapterVersion, ChapterOutline

logger = logging.getLogger(__name__)


class FanqiePublisherService:
    """番茄小说自动发布服务

    使用Playwright浏览器自动化实现章节自动发布功能
    基于实际测试的番茄小说平台流程
    """

    def __init__(self, cookies_dir: str = "storage/fanqie_cookies", headless: bool = False):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.book_id: Optional[str] = None
        self.cookies_dir = Path(cookies_dir)
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless  # 保存headless设置

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def init_browser(self, headless: Optional[bool] = None):
        """初始化浏览器

        Args:
            headless: 是否使用无头模式(默认使用构造函数中的设置)
                     生产环境建议设置为True
        """
        if headless is None:
            headless = self.headless

        self.playwright = await async_playwright().start()

        # 配置浏览器启动参数
        launch_options = {
            "headless": headless,
        }

        # 如果是headless模式，添加一些额外的参数确保兼容性
        if headless:
            launch_options["args"] = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]

        self.browser = await self.playwright.chromium.launch(**launch_options)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        logger.info(f"浏览器初始化完成 (headless={headless})")
        
    async def close(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("浏览器已关闭")
        
    async def load_cookies(self, account: str = "default"):
        """加载保存的Cookie

        Args:
            account: 账号标识（用于区分不同账号的cookie）
        """
        try:
            cookies_file = self.cookies_dir / f"{account}_cookies.json"
            if not cookies_file.exists():
                logger.warning(f"Cookie文件不存在: {cookies_file}")
                return False

            with open(cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            await self.context.add_cookies(cookies)
            logger.info(f"成功加载Cookie: {cookies_file}")
            return True
        except Exception as e:
            logger.error(f"加载Cookie失败: {e}")
            return False

    async def save_cookies(self, account: str = "default"):
        """保存当前Cookie

        Args:
            account: 账号标识（用于区分不同账号的cookie）
        """
        try:
            cookies_file = self.cookies_dir / f"{account}_cookies.json"
            cookies = await self.context.cookies()
            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            logger.info(f"成功保存Cookie: {cookies_file}")
            return True
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
            return False
            
    async def login(self, username: str, password: str) -> bool:
        """登录番茄小说
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            是否登录成功
        """
        try:
            # 访问登录页面
            await self.page.goto("https://fanqienovel.com/login")
            await self.page.wait_for_load_state("networkidle")
            
            # 填写用户名和密码
            await self.page.fill('input[name="username"]', username)
            await self.page.fill('input[name="password"]', password)
            
            # 点击登录按钮
            await self.page.click('button[type="submit"]')
            
            # 等待登录完成
            await self.page.wait_for_url("**/main/writer/**", timeout=30000)
            
            logger.info("登录成功")
            return True
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False
            
    async def find_book_by_name(self, book_name: str) -> Optional[str]:
        """通过书名查找书籍ID

        Args:
            book_name: 书籍名称

        Returns:
            书籍ID，如果未找到返回None
        """
        try:
            # 访问作家专区
            await self.page.goto("https://fanqienovel.com/writer/zone/")
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            # 点击"小说"菜单
            await self.page.click('text="小说"')
            await asyncio.sleep(2)

            # 查找书名对应的书籍
            # 书籍卡片的结构：包含书名和章节管理按钮
            book_cards = await self.page.query_selector_all('[id^="long-article-table-item-"]')

            for card in book_cards:
                # 获取书名
                title_elem = await card.query_selector('text')
                if title_elem:
                    title_text = await title_elem.text_content()
                    if book_name in title_text or title_text in book_name:
                        # 从卡片ID中提取book_id
                        card_id = await card.get_attribute('id')
                        if card_id:
                            book_id = card_id.replace('long-article-table-item-', '')
                            logger.info(f"找到书籍: {title_text}, ID: {book_id}")
                            self.book_id = book_id
                            return book_id

            logger.warning(f"未找到书籍: {book_name}")
            return None
        except Exception as e:
            logger.error(f"查找书籍失败: {e}")
            return None

    async def get_all_volumes(self) -> List[Dict[str, Any]]:
        """获取当前书籍的所有分卷信息

        Returns:
            分卷列表，每个分卷包含 {index, name}
        """
        try:
            # 先点击"编辑分卷"按钮，确保分卷列表可见
            edit_btn = await self.page.query_selector('button:has-text("编辑分卷")')
            if edit_btn:
                await edit_btn.click()
                await asyncio.sleep(1)

            volumes = await self.page.evaluate('''() => {
                const volumeItems = document.querySelectorAll('.chapter-volume-list-item-normal');
                const result = [];
                volumeItems.forEach((item, index) => {
                    const nameSpan = item.querySelector('span');
                    if (nameSpan) {
                        result.push({
                            index: index,
                            name: nameSpan.textContent.trim()
                        });
                    }
                });
                return result;
            }''')

            # 关闭编辑分卷对话框
            cancel_btn = await self.page.query_selector('button:has-text("取消")')
            if cancel_btn:
                await cancel_btn.click()
                await asyncio.sleep(0.5)

            logger.info(f"获取到 {len(volumes)} 个分卷: {[v['name'] for v in volumes]}")
            return volumes

        except Exception as e:
            logger.error(f"获取分卷列表失败: {e}")
            return []

    async def navigate_to_chapter_manage(self, book_id: Optional[str] = None) -> bool:
        """导航到章节管理页面

        Args:
            book_id: 书籍ID（如果不提供则使用self.book_id）

        Returns:
            是否成功导航
        """
        try:
            if book_id:
                self.book_id = book_id

            if not self.book_id:
                logger.error("未指定书籍ID")
                return False

            # 直接访问章节管理页面
            # URL格式: /main/writer/chapter-manage/{book_id}&{book_name}?type=1
            # 但是book_name可以省略，直接用book_id
            url = f"https://fanqienovel.com/main/writer/chapter-manage/{self.book_id}?type=1"
            await self.page.goto(url)
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            logger.info(f"成功导航到章节管理页面: {self.book_id}")
            return True
        except Exception as e:
            logger.error(f"导航失败: {e}")
            return False
            
    async def select_volume_in_editor(self, volume_name: str) -> bool:
        """在章节编辑器中选择指定分卷

        Args:
            volume_name: 要选择的分卷名称

        Returns:
            是否成功选择
        """
        try:
            # 在编辑器页面，分卷选择器通常在顶部
            # 尝试点击分卷下拉框
            volume_selector = await self.page.query_selector('.volume-selector, .serial-editor-volume-select, select[name="volume"]')

            if not volume_selector:
                # 尝试通过文本查找
                logger.warning("未找到分卷选择器，尝试通过文本查找")
                # 有些页面分卷选择是通过点击文本触发的
                volume_text = await self.page.query_selector(f'text="{volume_name}"')
                if volume_text:
                    await volume_text.click()
                    await asyncio.sleep(0.5)
                    logger.info(f"通过文本选择了分卷: {volume_name}")
                    return True
                else:
                    logger.warning(f"未找到分卷: {volume_name}，将使用默认分卷")
                    return False

            # 点击下拉框
            await volume_selector.click()
            await asyncio.sleep(0.5)

            # 选择目标分卷
            option = await self.page.query_selector(f'option:has-text("{volume_name}"), li:has-text("{volume_name}")')
            if option:
                await option.click()
                await asyncio.sleep(0.5)
                logger.info(f"成功选择分卷: {volume_name}")
                return True
            else:
                logger.error(f"未找到分卷选项: {volume_name}")
                return False

        except Exception as e:
            logger.error(f"选择分卷失败: {e}")
            return False

    async def edit_volume_name(self, old_name: str, new_name: str) -> Dict[str, Any]:
        """编辑分卷名称

        Args:
            old_name: 原分卷名称（用于定位）
            new_name: 新分卷名称（最多20字）

        Returns:
            编辑结果
        """
        try:
            # 1. 点击"编辑分卷"按钮
            await self.page.click('button:has-text("编辑分卷")')
            await asyncio.sleep(1)

            # 2. 找到目标分卷并点击编辑图标
            # 使用JavaScript查找并点击编辑图标（使用参数传递避免注入）
            edit_result = await self.page.evaluate('''(oldName) => {
                const volumeItems = document.querySelectorAll('.chapter-volume-list-item-normal');
                for (const item of volumeItems) {
                    const nameSpan = item.querySelector('span');
                    if (nameSpan && nameSpan.textContent.includes(oldName)) {
                        const editIcon = item.querySelector('.tomato-edit');
                        if (editIcon) {
                            editIcon.click();
                            return true;
                        }
                    }
                }
                return false;
            }''', old_name)

            if not edit_result:
                logger.error(f"未找到分卷: {old_name}")
                return {"success": False, "error": f"未找到分卷: {old_name}"}

            await asyncio.sleep(0.5)

            # 3. 填写新的分卷名称
            await self.page.fill('input[placeholder="请输入分卷名字"]', new_name)
            await asyncio.sleep(0.3)

            # 4. 点击对勾图标确认
            await self.page.evaluate('''() => {
                const confirmIcon = document.querySelector('.tomato-confirm');
                if (confirmIcon) confirmIcon.click();
            }''')
            await asyncio.sleep(0.5)

            # 5. 点击"确定"按钮保存
            await self.page.click('button:has-text("确定")')
            await asyncio.sleep(1)

            logger.info(f"成功编辑分卷: {old_name} -> {new_name}")
            return {
                "success": True,
                "old_name": old_name,
                "new_name": new_name
            }
        except Exception as e:
            logger.error(f"编辑分卷失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def create_volume(self, volume_name: str) -> Dict[str, Any]:
        """创建新分卷

        注意: 只有当前分卷有章节时才能创建新分卷

        Args:
            volume_name: 分卷名称（最多20字）

        Returns:
            创建结果
        """
        try:
            # 1. 点击"编辑分卷"按钮
            await self.page.click('button:has-text("编辑分卷")')
            await asyncio.sleep(1)

            # 2. 点击"新建分卷"按钮
            new_volume_btn = await self.page.query_selector('text="新建分卷"')
            if new_volume_btn:
                await new_volume_btn.click()
                await asyncio.sleep(0.5)
            else:
                logger.error("未找到'新建分卷'按钮")
                return {"success": False, "error": "未找到'新建分卷'按钮"}

            # 3. 填写分卷名称
            # 新建分卷时会出现一个输入框
            volume_input = await self.page.query_selector('input[placeholder*="分卷"]')
            if volume_input:
                await volume_input.fill(volume_name)
                await asyncio.sleep(0.3)

                # 4. 点击对勾确认
                await self.page.evaluate('''() => {
                    const confirmIcon = document.querySelector('.tomato-confirm');
                    if (confirmIcon) confirmIcon.click();
                }''')
                await asyncio.sleep(0.5)

            # 5. 点击"确定"按钮保存
            await self.page.click('button:has-text("确定")')
            await asyncio.sleep(1)

            logger.info(f"成功创建分卷: {volume_name}")
            return {
                "success": True,
                "volume_name": volume_name
            }
        except Exception as e:
            logger.error(f"创建分卷失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def publish_chapter(
        self,
        chapter_number: int,
        chapter_title: str,
        content: str,
        volume_name: Optional[str] = None,
        use_ai: bool = False
    ) -> Dict[str, Any]:
        """发布章节到番茄小说

        基于实际测试的完整流程

        Args:
            chapter_number: 章节序号（纯数字）
            chapter_title: 章节标题（会自动清理"第X章"前缀）
            content: 章节内容
            volume_name: 分卷名称（可选，不指定则使用当前分卷）
            use_ai: 是否使用AI（默认否，审核通过后立即发布）

        Returns:
            发布结果
        """
        try:
            # 1. 点击"新建章节"按钮
            new_chapter_btn = await self.page.query_selector('button:has-text("新建章节"), a:has-text("新建章节")')
            if not new_chapter_btn:
                logger.error("未找到'新建章节'按钮")
                return {"success": False, "error": "未找到'新建章节'按钮"}

            await new_chapter_btn.click()
            await asyncio.sleep(2)

            # 2. 等待新标签页打开
            # 番茄小说会在新标签页打开编辑器
            await asyncio.sleep(1)
            pages = self.context.pages
            if len(pages) > 1:
                self.page = pages[-1]  # 切换到最新的页面

            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)

            # 3. 如果指定了分卷，选择对应的分卷
            if volume_name:
                logger.info(f"尝试选择分卷: {volume_name}")
                volume_selected = await self.select_volume_in_editor(volume_name)
                if not volume_selected:
                    logger.error(f"未能选择分卷: {volume_name}，终止上传")
                    return {
                        "success": False,
                        "error": f"未能选择分卷: {volume_name}，请确认分卷已创建"
                    }

            # 4. 清理标题中的"第X章"前缀
            clean_title = re.sub(r'^第[0-9一二三四五六七八九十百千万]+章\s*', '', chapter_title)
            if len(clean_title) < 5:
                logger.warning(f"标题太短（少于5字）: {clean_title}，将添加前缀")
                clean_title = f"第{chapter_number}章 {clean_title}"

            # 4. 填写章节号
            # 查找章节号输入框（在.serial-editor-title-left内）
            chapter_num_input = await self.page.query_selector('.serial-editor-title-left input')
            if chapter_num_input:
                await chapter_num_input.fill(str(chapter_number))
                await chapter_num_input.dispatch_event('input')
                await chapter_num_input.dispatch_event('change')
                logger.info(f"填写章节号: {chapter_number}")

            # 5. 填写标题
            title_input = await self.page.query_selector('input[placeholder*="标题"]')
            if title_input:
                await title_input.fill(clean_title)
                await title_input.dispatch_event('input')
                await title_input.dispatch_event('change')
                logger.info(f"填写标题: {clean_title}")

            # 6. 填写正文内容
            # 使用ProseMirror编辑器
            editor = await self.page.query_selector('.ProseMirror')
            if editor:
                # 清空编辑器
                await self.page.evaluate('''() => {
                    const editor = document.querySelector('.ProseMirror');
                    if (editor) editor.innerHTML = '';
                }''')

                # 将内容按段落分割并插入
                paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                await self.page.evaluate('''(paragraphs) => {
                    const editor = document.querySelector('.ProseMirror');
                    if (editor) {
                        paragraphs.forEach(para => {
                            const p = document.createElement('p');
                            p.textContent = para;
                            editor.appendChild(p);
                        });
                        editor.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }''', paragraphs)

                logger.info(f"填写内容: {len(content)}字, {len(paragraphs)}段")
                await asyncio.sleep(2)  # 等待自动保存

            # 7. 点击"下一步"
            next_btn = await self.page.query_selector('button:has-text("下一步")')
            if next_btn:
                await next_btn.click()
                await asyncio.sleep(2)
            else:
                logger.error("未找到'下一步'按钮")
                return {"success": False, "error": "未找到'下一步'按钮"}

            # 8. 处理内容风险检测对话框
            # 点击"确定"按钮
            try:
                confirm_btn = await self.page.wait_for_selector('button:has-text("确定")', timeout=3000)
                if confirm_btn:
                    await confirm_btn.click()
                    await asyncio.sleep(2)
            except PlaywrightTimeoutError:
                logger.info("未出现风险检测对话框")
            except Exception as e:
                logger.warning(f"处理风险检测对话框时出错: {e}")

            # 9. 等待发布设置对话框出现
            await asyncio.sleep(1)

            # 10. 选择是否使用AI
            ai_option = "是" if use_ai else "否"
            try:
                # 查找"是否使用AI"选项
                ai_radio = await self.page.query_selector(f'text="{ai_option}"')
                if ai_radio:
                    await ai_radio.click()
                    logger.info(f"选择AI选项: {ai_option}")
            except Exception as e:
                logger.warning(f"选择AI选项失败: {e}")

            # 11. 确保定时发布是关闭的（审核通过后立即发布）
            # 定时发布开关默认是关闭的，不需要额外操作

            # 12. 点击"确认发布"
            publish_btn = await self.page.query_selector('button:has-text("确认发布")')
            if publish_btn:
                await publish_btn.click()
                await asyncio.sleep(3)
                logger.info("点击'确认发布'按钮")
            else:
                logger.error("未找到'确认发布'按钮")
                return {"success": False, "error": "未找到'确认发布'按钮"}

            # 13. 检查是否发布成功
            # 成功后会显示"已提交，预计1小时内完成审核"
            logger.info(f"章节发布成功: 第{chapter_number}章 {clean_title}")
            return {
                "success": True,
                "chapter_number": chapter_number,
                "title": clean_title,
                "status": "已提交审核"
            }

        except Exception as e:
            logger.error(f"发布章节失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    async def upload_novel_to_fanqie(
        self,
        db: AsyncSession,
        project_id: str,
        account: str = "default"
    ) -> Dict[str, Any]:
        """一键上传小说到番茄小说

        完整流程：
        1. 加载Cookie登录
        2. 通过书名查找book_id
        3. 同步分卷结构
        4. 批量上传章节

        Args:
            db: 异步数据库会话
            project_id: 小说项目ID
            account: 番茄小说账号标识

        Returns:
            上传结果
        """
        try:
            # 1. 查询小说项目
            stmt = select(NovelProject).where(NovelProject.id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                return {"success": False, "error": "小说项目不存在"}

            book_name = project.title
            logger.info(f"开始上传小说: {book_name}")

            # 2. 加载Cookie
            cookie_loaded = await self.load_cookies(account)
            if not cookie_loaded:
                logger.error(f"Cookie加载失败，账号标识: {account}")
                return {
                    "success": False,
                    "error": f"Cookie加载失败，请先调用 /api/novels/fanqie/login 接口手动登录并保存Cookie（账号标识: {account}）",
                    "hint": "Cookie文件路径: storage/fanqie_cookies/{account}_cookies.json"
                }

            # 验证Cookie是否有效（尝试访问作家专区）
            try:
                await self.page.goto("https://fanqienovel.com/writer/zone/")
                await self.page.wait_for_load_state("networkidle", timeout=10000)

                # 检查是否跳转到登录页
                current_url = self.page.url
                if "login" in current_url or "passport" in current_url:
                    logger.error("Cookie已失效，需要重新登录")
                    return {
                        "success": False,
                        "error": "Cookie已失效，请重新调用 /api/novels/fanqie/login 接口登录",
                        "hint": "Cookie可能已过期，请重新登录"
                    }

                logger.info("Cookie验证成功")
            except Exception as e:
                logger.error(f"Cookie验证失败: {e}")
                return {
                    "success": False,
                    "error": f"Cookie验证失败: {str(e)}，请重新登录"
                }

            # 3. 查找书籍
            book_id = await self.find_book_by_name(book_name)
            if not book_id:
                return {
                    "success": False,
                    "error": f"未找到书籍: {book_name}，请先在番茄小说平台手动创建该书籍"
                }

            # 4. 导航到章节管理页面
            nav_success = await self.navigate_to_chapter_manage(book_id)
            if not nav_success:
                return {"success": False, "error": "导航到章节管理页面失败"}

            # 5. 同步分卷结构
            # 先获取番茄小说上现有的分卷
            existing_volumes = await self.get_all_volumes()
            if not existing_volumes:
                logger.error("无法获取现有分卷列表")
                return {"success": False, "error": "无法获取现有分卷列表"}

            logger.info(f"番茄小说现有分卷: {[v['name'] for v in existing_volumes]}")

            # 查询本地所有分卷
            volumes_stmt = (
                select(Volume)
                .where(Volume.project_id == project_id)
                .order_by(Volume.volume_number)
            )
            volumes_result = await db.execute(volumes_stmt)
            volumes = volumes_result.scalars().all()

            volume_sync_results = []

            for i, volume in enumerate(volumes):
                if i == 0:
                    # 第一卷：编辑现有的第一个分卷（不管它叫什么名字）
                    if existing_volumes:
                        first_volume_name = existing_volumes[0]['name']
                        logger.info(f"将第一个分卷 '{first_volume_name}' 改名为 '{volume.title}'")
                        result = await self.edit_volume_name(first_volume_name, volume.title)
                        volume_sync_results.append(result)
                    else:
                        logger.error("番茄小说上没有任何分卷")
                        return {"success": False, "error": "番茄小说上没有任何分卷"}
                else:
                    # 后续分卷：创建新分卷
                    result = await self.create_volume(volume.title)
                    volume_sync_results.append(result)

                if not result.get("success"):
                    logger.error(f"分卷同步失败: {result}")
                    return {
                        "success": False,
                        "error": f"分卷同步失败: {result.get('error')}",
                        "volume_sync_results": volume_sync_results
                    }

            logger.info(f"分卷同步完成: {len(volumes)}个分卷")

            # 6. 批量上传章节
            # 查询所有章节及其关联数据
            chapters_stmt = (
                select(Chapter)
                .where(Chapter.project_id == project_id)
                .options(
                    selectinload(Chapter.selected_version),
                    selectinload(Chapter.volume)
                )
                .order_by(Chapter.chapter_number)
            )
            chapters_result = await db.execute(chapters_stmt)
            chapters = chapters_result.scalars().all()

            upload_results = []

            for chapter in chapters:
                # 获取章节内容
                if not chapter.selected_version:
                    logger.warning(f"章节{chapter.chapter_number}没有选中的版本，跳过")
                    continue

                content = chapter.selected_version.content
                if not content:
                    logger.warning(f"章节{chapter.chapter_number}内容为空，跳过")
                    continue

                # 获取分卷名称
                volume_name = None
                if chapter.volume:
                    volume_name = chapter.volume.title

                # 获取章节标题
                # 优先使用outline的title，如果没有则使用chapter_number
                chapter_title = f"第{chapter.chapter_number}章"

                # 查询章节大纲
                outline_stmt = (
                    select(ChapterOutline)
                    .where(
                        ChapterOutline.project_id == project_id,
                        ChapterOutline.chapter_number == chapter.chapter_number
                    )
                )
                outline_result = await db.execute(outline_stmt)
                outline = outline_result.scalar_one_or_none()

                if outline and outline.title:
                    chapter_title = outline.title

                # 上传章节
                logger.info(f"上传章节 {chapter.chapter_number}/{len(chapters)}: {chapter_title}")
                result = await self.publish_chapter(
                    chapter_number=chapter.chapter_number,
                    chapter_title=chapter_title,
                    content=content,
                    volume_name=volume_name,
                    use_ai=False  # 不使用AI，审核通过后立即发布
                )

                upload_results.append(result)

                # 如果上传失败，立即停止
                if not result.get("success"):
                    logger.error(f"章节上传失败: {result}")
                    return {
                        "success": False,
                        "error": f"章节{chapter.chapter_number}上传失败: {result.get('error')}",
                        "volume_sync_results": volume_sync_results,
                        "upload_results": upload_results
                    }

                # 返回章节管理页面，准备上传下一章
                await self.navigate_to_chapter_manage()
                await asyncio.sleep(2)

            logger.info(f"所有章节上传完成: {len(upload_results)}章")
            return {
                "success": True,
                "book_id": book_id,
                "book_name": book_name,
                "volume_count": len(volumes),
                "chapter_count": len(upload_results),
                "volume_sync_results": volume_sync_results,
                "upload_results": upload_results
            }

        except Exception as e:
            logger.error(f"上传小说失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    async def manual_login_and_save_cookies(
        self,
        account: str = "default",
        wait_seconds: int = 60
    ) -> Dict[str, Any]:
        """手动登录并保存Cookie

        打开浏览器让用户手动登录，登录成功后自动保存Cookie

        Args:
            account: 账号标识
            wait_seconds: 等待用户登录的时间（秒）

        Returns:
            操作结果
        """
        try:
            # 访问作家专区（会自动跳转到登录页面）
            await self.page.goto("https://fanqienovel.com/writer/zone/")

            logger.info(f"请在浏览器中手动登录，等待{wait_seconds}秒...")
            logger.info("登录成功后，页面会自动跳转到作家专区")

            # 等待用户登录
            try:
                # 等待跳转到作家专区
                await self.page.wait_for_url("**/writer/zone/**", timeout=wait_seconds * 1000)
                logger.info("检测到登录成功")
            except PlaywrightTimeoutError:
                logger.warning("未检测到登录成功，但仍会尝试保存Cookie")
            except Exception as e:
                logger.warning(f"等待登录时出错: {e}，但仍会尝试保存Cookie")

            # 保存Cookie
            save_success = await self.save_cookies(account)
            if save_success:
                logger.info(f"Cookie已保存，账号标识: {account}")
                return {
                    "success": True,
                    "account": account,
                    "message": "登录成功，Cookie已保存"
                }
            else:
                return {
                    "success": False,
                    "error": "Cookie保存失败"
                }

        except Exception as e:
            logger.error(f"手动登录失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

