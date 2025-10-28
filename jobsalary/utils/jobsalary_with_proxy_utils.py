"""
www.jobsalary.com.tw 工具: 有代理版本,依赖库 pip install aiohttp_socks
"""
import asyncio
import json
import logging
import pathlib
import random
from typing import Optional, Dict, Any

import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
COMMON_HEADERS = {
    "User-Agent": USER_AGENT,
    # "Referer": "https://www.jobsalary.com.tw/"
}
SCRIPT_ROOT = pathlib.Path(__file__).parent
TIMEOUT = ClientTimeout(total=300)


class ProxyManager:
    """代理管理器"""

    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None):
        self.proxy_config = proxy_config or {}

    def get_proxy_url(self) -> Optional[str]:
        """根据配置生成代理URL"""
        if not self.proxy_config:
            return None

        proxy_type = self.proxy_config.get('type', 'http').lower()
        host = self.proxy_config.get('host', '')
        port = self.proxy_config.get('port', '')
        username = self.proxy_config.get('username')
        password = self.proxy_config.get('password')

        if not host or not port:
            return None

        # 构建代理URL
        if username and password:
            # 有账号密码的代理
            if proxy_type in ['http', 'https']:
                return f"{proxy_type}://{username}:{password}@{host}:{port}"
            elif proxy_type == 'socks5':
                return f"socks5://{username}:{password}@{host}:{port}"
            else:
                return f"{proxy_type}://{username}:{password}@{host}:{port}"
        else:
            # 无账号密码的代理
            if proxy_type in ['http', 'https']:
                return f"{proxy_type}://{host}:{port}"
            elif proxy_type == 'socks5':
                return f"socks5://{host}:{port}"
            else:
                return f"{proxy_type}://{host}:{port}"


class JobSalaryUtils:
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None):
        # 检索岗位薪资
        self.base_url_query = "https://www.jobsalary.com.tw/salarysummary.aspx?codeNo="
        # 获取岗位信息
        self.base_url_job_menu = "https://www.jobsalary.com.tw/includesU/tcodeMenu/data/tCodeDutyNM.js?v="

        # 初始化代理管理器
        self.proxy_manager = ProxyManager(proxy_config)

    # async def _make_request(self, url: str, headers: Dict[str, str]) -> Optional[str]:
    #     """统一的请求方法，支持代理"""
    #     proxy_url = self.proxy_manager.get_proxy_url()
    #
    #     try:
    #         connector = None
    #         # 如果是SOCKS5代理，需要特殊处理
    #         if proxy_url and proxy_url.startswith('socks5'):
    #             try:
    #                 from aiohttp_socks import ProxyConnector
    #                 connector = ProxyConnector.from_url(proxy_url)
    #             except ImportError:
    #                 logging.warning("SOCKS5代理需要安装 aiohttp_socks: pip install aiohttp_socks")
    #                 # 回退到普通代理处理
    #                 proxy_url = None
    #
    #         async with aiohttp.ClientSession(
    #                 timeout=TIMEOUT,
    #                 connector=connector
    #         ) as session:
    #             async with session.get(
    #                     url,
    #                     headers=headers,
    #                     proxy=proxy_url if not connector else None
    #             ) as response:
    #                 if response.status == 200:
    #                     return await response.text()
    #                 else:
    #                     logging.error(f"请求失败，状态码: {response.status}, URL: {url}")
    #                     return None
    #     except Exception as e:
    #         logging.exception(f"请求发生错误: {e}, URL: {url}")
    #         return None
    async def _make_request(self, url: str, method: str = 'GET', headers: Dict[str, str] = None,
                            data: Any = None, form_data: aiohttp.FormData = None) -> Optional[str]:
        """统一的请求方法，支持代理"""
        proxy_url = self.proxy_manager.get_proxy_url()

        try:
            # 创建忽略SSL验证的连接器
            connector = aiohttp.TCPConnector(ssl=False)

            async with aiohttp.ClientSession(connector=connector) as session:
                if method.upper() == 'GET':
                    async with session.get(
                            url,
                            headers=headers,
                            proxy=proxy_url
                    ) as response:
                        if response.status == 200:
                            return await response.text()
                        else:
                            logging.error(f"请求失败，状态码: {response.status}, URL: {url}")
                            return None
                else:  # POST
                    async with session.post(
                            url,
                            headers=headers,
                            data=data or form_data,
                            proxy=proxy_url
                    ) as response:
                        if response.status == 200:
                            return await response.text()
                        else:
                            logging.error(f"请求失败，状态码: {response.status}, URL: {url}")
                            return None
        except Exception as e:
            logging.exception(f"请求发生错误: {e}, URL: {url}")
            return None

    async def get_jobs_menu(self) -> list:
        """获取工作岗位列表"""
        v = random.random()
        url = f"{self.base_url_job_menu}{v}"
        headers = COMMON_HEADERS

        html = await self._make_request(url, headers)
        if html:
            results = await self.extract_jobs_data(html)
            return results
        return []

    @staticmethod
    async def extract_jobs_data(html: str) -> list:
        """
        解析出岗位信息
        Args:
            html:

        Returns:

        """
        strip_s = "tcodeParams['tCodeDutyNM'] = "
        e1 = html.find(strip_s)
        if e1:
            html = html[e1 + len(strip_s)]
        s = html.replace(";", "")
        try:
            dic = json.loads(s)
            if not dic.get("arr"):
                return []
            menus = dic.get("arr")
            # 只返回ct=3的岗位（最终检索的岗位）
            lis = [{"jobCode": v["k"], "jobName": v["v"]} for v in menus if v.get("ct") == 3]
            return lis
        except Exception as e:
            logging.exception(f"解析数据失败: {e}")
            return []

    async def find_job_salary_back_markdown(self, job_code: str, job_name: str) -> str:
        """
        通过岗位名称/代码进行检索

        Args:
            job_code: 岗位代码
            job_name: 岗位名称

        Returns: markdown格式，如果找不到记录返回空

        """
        # 查询公司的前置信息
        rs = await self.find_job_salary(job_code)
        if not rs and type(rs) != list:
            return ""

        # 形成markdown文档
        lines = ""
        for row in rs:
            years = ",".join(row["years"])
            salaries = ",".join(row["salaries"])
            lines += f"{row['education_level']} : {years} => {salaries}\n"

        markdown = f"""
# {job_name} 岗位平均薪资情况

{lines}
"""
        return markdown

    async def find_job_salary(self, keyword: str) -> list:
        """
        通过岗位代码检索岗位的薪资水平

        Args:
            keyword: 岗位代码

        Returns: markdown格式，如果找不到记录返回空

        """
        # 定义请求头
        headers = COMMON_HEADERS
        # 构建目标url
        url = f"{self.base_url_query}{keyword}"

        html = await self._make_request(url, headers)
        if html:
            results = self.extract_salary_data(html)
            return results
        return []

    def extract_salary_data(self, html_content: str):
        """
        按照指定路径提取薪资数据
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. 先找到 <div id="main_pnlDesc">
        main_container = soup.find("div", id="main_pnlDesc")

        if not main_container:
            logging.warning("未找到 main_pnlDesc 容器")
            return []

        # 2. 再找到它下面的所有 <div class="topicContentBox">
        topic_boxes = main_container.find_all("div", class_="topicContentBox")

        results = []

        for topic_box in topic_boxes:
            # 获取对应的教育水平（从前面的a标签中获取）
            education_level = self.get_education_level(topic_box)

            # 3.1 找到 <div class="avgSalaryListPart01">，提取ol>li的文本内容
            years_part = topic_box.find("div", class_="avgSalaryListPart01")
            years = []
            if years_part:
                years_ol = years_part.find("ol")
                if years_ol:
                    years_li = years_ol.find_all("li")
                    years = [li.get_text(strip=True) for li in years_li]

            # 3.2 找到 <div class="avgSalaryListPart02">，提取ol>li的文本内容
            salary_part = topic_box.find("div", class_="avgSalaryListPart02")
            salaries = []
            if salary_part:
                salary_ol = salary_part.find("ol")
                if salary_ol:
                    salary_li = salary_ol.find_all("li")
                    salaries = [li.get_text(strip=True) for li in salary_li]

            # 确保数据对应且不为空
            if years and salaries and len(years) == len(salaries):
                results.append({
                    "education_level": education_level,
                    "years": years,
                    "salaries": salaries
                })

        return results

    @staticmethod
    def get_education_level(topic_box):
        """
        从topicBox前面的a标签中获取教育水平
        """
        # 查找前一个兄弟元素，可能是a标签
        prev_element = topic_box.find_previous_sibling("a", class_="slideToggle")

        if prev_element:
            # 在a标签中查找h2标签
            h2_element = prev_element.find("h2", class_="jobEducationTitle")
            if h2_element:
                # h2中有多个span，第二个是教育水平
                spans = h2_element.find_all("span")
                if len(spans) >= 2:
                    return spans[1].get_text(strip=True)

        return "未知教育水平"


def jobs(is_update: bool = False, proxy_config: Optional[Dict[str, Any]] = None) -> list:
    """
    获取工作岗位信息

    Args:
        is_update: 是否更新，如果为True将会从拉取最新的记录（慢），否则直接加载已有记录
        proxy_config: 代理配置字典

    Returns:

    """
    try:
        job_menu_path = f"{SCRIPT_ROOT}/jobs_menus.json"
        if is_update:
            # 加载新记录
            job_utils = JobSalaryUtils(proxy_config)
            lis = asyncio.run(job_utils.get_jobs_menu())
            if lis:
                # 更新最新的工作岗位信息
                with open(job_menu_path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(lis))
                return lis
        # 加载旧记录
        # 从之前的记录中加载
        with open(job_menu_path, "r", encoding="utf-8") as f:
            s = f.read()
            lis = json.loads(s)
        return lis
    except Exception as e:
        logging.exception(f"加载工作岗位异常: {e}")
        return []


def crawl(query: str, proxy_config: Optional[Dict[str, Any]] = None) -> str:
    """
    进行爬取

    Args:
        query: 公司名称、公司编码、公司高管名称等
        proxy_config: 代理配置字典

    Returns: markdown格式，如果找不到记录返回空

    """
    if not query or not query.strip():
        return ""

    # 获取岗位列表
    jobs_menu = jobs(proxy_config=proxy_config)
    if not jobs_menu:
        return ""
    # 匹配出岗位代码和岗位名称
    job_code = ""
    job_name = ""
    for row in jobs_menu:
        if row.get("jobCode") == query or row.get("jobName") == query:
            job_code = row.get("jobCode")
            job_name = row.get("jobName")
            break

    # 初始化工具
    job_utils = JobSalaryUtils(proxy_config)

    # 检索岗位的薪资
    rs = asyncio.run(job_utils.find_job_salary_back_markdown(job_code, job_name))
    return rs
