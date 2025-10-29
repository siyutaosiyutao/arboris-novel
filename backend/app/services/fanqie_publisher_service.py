"""番茄小说自动发布服务"""
import asyncio
import logging
import re
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class FanqiePublisherService:
    """番茄小说自动发布服务
    
    使用Playwright浏览器自动化实现章节自动发布功能
    """
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.book_id: Optional[str] = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
        
    async def init_browser(self, headless: bool = False):
        """初始化浏览器
        
        Args:
            headless: 是否使用无头模式(默认False,方便调试)
        """
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        logger.info("浏览器初始化完成")
        
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
        
    async def load_cookies(self, cookies_file: str = "fanqie_cookies.json"):
        """加载保存的Cookie
        
        Args:
            cookies_file: Cookie文件路径
        """
        try:
            import json
            with open(cookies_file, 'r') as f:
                cookies = json.load(f)
            await self.context.add_cookies(cookies)
            logger.info(f"成功加载Cookie: {cookies_file}")
            return True
        except FileNotFoundError:
            logger.warning(f"Cookie文件不存在: {cookies_file}")
            return False
        except Exception as e:
            logger.error(f"加载Cookie失败: {e}")
            return False
            
    async def save_cookies(self, cookies_file: str = "fanqie_cookies.json"):
        """保存当前Cookie
        
        Args:
            cookies_file: Cookie文件路径
        """
        try:
            import json
            cookies = await self.context.cookies()
            with open(cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
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
            
    async def navigate_to_book(self, book_id: str) -> bool:
        """导航到指定书籍的管理页面
        
        Args:
            book_id: 书籍ID
            
        Returns:
            是否成功导航
        """
        try:
            self.book_id = book_id
            url = f"https://fanqienovel.com/main/writer/book-manage"
            await self.page.goto(url)
            await self.page.wait_for_load_state("networkidle")
            logger.info(f"成功导航到书籍管理页面")
            return True
        except Exception as e:
            logger.error(f"导航失败: {e}")
            return False
            
    async def create_volume(self, volume_name: str) -> Dict[str, Any]:
        """创建新分卷
        
        注意:只有当前分卷有章节时才能创建新分卷
        
        Args:
            volume_name: 分卷名称(最多20字)
            
        Returns:
            创建结果
        """
        try:
            # 点击"编辑分卷"按钮
            await self.page.click('button:has-text("编辑分卷")')
            await asyncio.sleep(1)
            
            # 点击"新建分卷"按钮
            await self.page.click('button:has-text("新建分卷")')
            await asyncio.sleep(0.5)
            
            # 填写分卷名称
            await self.page.fill('input[placeholder="请输入分卷名称"]', volume_name)
            
            # 点击确认
            await self.page.click('button:has-text("确定")')
            await asyncio.sleep(1)
            
            # 检查是否有错误提示
            error_text = await self.page.text_content('.error-message, .toast-message')
            if error_text and "不支持" in error_text:
                logger.warning(f"创建分卷失败: {error_text}")
                return {
                    "success": False,
                    "error": error_text,
                    "message": "无法创建多个空分卷,请先在当前分卷发布章节"
                }
            
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
        run_risk_detection: bool = True,
        auto_correct_errors: bool = True,
        use_ai: bool = False,
        scheduled_publish: bool = False
    ) -> Dict[str, Any]:
        """发布章节到番茄小说
        
        Args:
            chapter_number: 章节序号(纯数字)
            chapter_title: 章节标题(不要包含"第X章")
            content: 章节内容
            volume_name: 分卷名称(可选)
            run_risk_detection: 是否运行风险检测
            auto_correct_errors: 是否自动纠正错别字
            use_ai: 是否使用AI
            scheduled_publish: 是否定时发布
            
        Returns:
            发布结果
        """
        try:
            # 1. 点击"创建章节"按钮
            await self.page.click('button:has-text("创建章节")')
            await asyncio.sleep(2)
            
            # 2. 切换到新打开的标签页
            pages = self.context.pages
            if len(pages) > 1:
                self.page = pages[-1]  # 切换到最新的页面
            
            await self.page.wait_for_load_state("networkidle")
            
            # 3. 关闭可能出现的引导弹窗
            try:
                close_button = await self.page.query_selector('button.close, .modal-close')
                if close_button:
                    await close_button.click()
                    await asyncio.sleep(0.5)
            except:
                pass
            
            # 4. 清理标题中的"第X章"前缀
            clean_title = re.sub(r'^第[0-9一二三四五六七八九十百千万]+章\s*', '', chapter_title)
            
            # 5. 填写章节标题
            await self.page.fill('input[placeholder="请输入标题"]', clean_title)
            logger.info(f"填写标题: {clean_title}")
            
            # 6. 填写章节内容
            await self.page.fill('textarea, .ProseMirror', content)
            logger.info(f"填写内容: {len(content)}字")
            
            await asyncio.sleep(1)
            
            # 7. 运行风险检测
            if run_risk_detection and len(content) >= 1000:
                await self._run_risk_detection()
            
            # 8. 运行智能纠错
            if auto_correct_errors:
                await self._run_error_correction()
            
            # 9. 填写章节序号
            await self.page.fill('input[placeholder="请输入章节序号"]', str(chapter_number))
            logger.info(f"填写章节序号: {chapter_number}")
            
            # 10. 点击"下一步"
            await self.page.click('button:has-text("下一步")')
            await asyncio.sleep(2)
            
            # 11. 选择分卷(如果指定)
            if volume_name:
                try:
                    await self.page.click(f'text="{volume_name}"')
                    logger.info(f"选择分卷: {volume_name}")
                except:
                    logger.warning(f"未找到分卷: {volume_name},使用默认分卷")
            
            # 12. 选择是否使用AI
            ai_option = "是" if use_ai else "否"
            await self.page.click(f'text="{ai_option}"')
            logger.info(f"是否使用AI: {ai_option}")
            
            # 13. 定时发布设置
            if not scheduled_publish:
                # 关闭定时发布
                try:
                    switch = await self.page.query_selector('.switch, input[type="checkbox"]')
                    if switch:
                        is_checked = await switch.is_checked()
                        if is_checked:
                            await switch.click()
                except:
                    pass
            
            # 14. 点击"确认发布"
            await self.page.click('button:has-text("确认发布")')
            await asyncio.sleep(3)
            
            # 15. 检查发布结果
            success_indicator = await self.page.query_selector('text="审核中", text="发布成功"')
            if success_indicator:
                logger.info(f"章节发布成功: 第{chapter_number}章 {clean_title}")
                return {
                    "success": True,
                    "chapter_number": chapter_number,
                    "title": clean_title,
                    "status": "审核中"
                }
            else:
                logger.error("发布失败,未找到成功标识")
                return {
                    "success": False,
                    "error": "未找到发布成功标识"
                }
                
        except Exception as e:
            logger.error(f"发布章节失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _run_risk_detection(self) -> Dict[str, Any]:
        """运行风险检测

        Returns:
            检测结果
        """
        try:
            # 点击"风险提示"按钮
            await self.page.click('button:has-text("风险提示")')
            await asyncio.sleep(1)

            # 点击"开启检测"
            await self.page.click('button:has-text("开启检测")')
            await asyncio.sleep(2)

            # 点击"确认"
            try:
                await self.page.click('button:has-text("确认")', timeout=3000)
                await asyncio.sleep(3)
            except:
                pass

            # 读取检测结果
            result_text = await self.page.text_content('.risk-result, .detection-result')
            logger.info(f"风险检测结果: {result_text}")

            return {
                "success": True,
                "result": result_text
            }
        except Exception as e:
            logger.warning(f"风险检测失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _run_error_correction(self) -> Dict[str, Any]:
        """运行智能纠错

        Returns:
            纠错结果
        """
        try:
            # 切换到"智能纠错"标签
            await self.page.click('text="智能纠错"')
            await asyncio.sleep(1)

            # 点击"重新检测"或"开启检测"
            try:
                await self.page.click('button:has-text("重新检测")', timeout=2000)
            except:
                await self.page.click('button:has-text("开启检测")', timeout=2000)

            await asyncio.sleep(3)

            # 检查是否有错别字
            error_count_elem = await self.page.query_selector('text=/检测到.*处错别字/')
            if error_count_elem:
                # 有错别字,点击"替换全部"
                await self.page.click('button:has-text("替换全部")')
                await asyncio.sleep(1)
                logger.info("已自动替换所有错别字")
                return {
                    "success": True,
                    "corrected": True
                }
            else:
                logger.info("未检测到错别字")
                return {
                    "success": True,
                    "corrected": False
                }
        except Exception as e:
            logger.warning(f"智能纠错失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def batch_publish_chapters(
        self,
        chapters: list[Dict[str, Any]],
        interval_seconds: int = 5
    ) -> list[Dict[str, Any]]:
        """批量发布章节

        Args:
            chapters: 章节列表,每个章节包含:
                - chapter_number: 章节序号
                - title: 章节标题
                - content: 章节内容
                - volume_name: 分卷名称(可选)
            interval_seconds: 发布间隔(秒)

        Returns:
            发布结果列表
        """
        results = []

        for i, chapter in enumerate(chapters):
            logger.info(f"正在发布第 {i+1}/{len(chapters)} 章...")

            result = await self.publish_chapter(
                chapter_number=chapter["chapter_number"],
                chapter_title=chapter["title"],
                content=chapter["content"],
                volume_name=chapter.get("volume_name"),
            )

            results.append(result)

            # 如果不是最后一章,等待间隔
            if i < len(chapters) - 1:
                logger.info(f"等待 {interval_seconds} 秒后发布下一章...")
                await asyncio.sleep(interval_seconds)

        return results

