"""
https://www.csb.gov.hk 工具
"""
import asyncio
import json
import logging
import pathlib
import re
import unicodedata
from typing import Dict

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


def clean_text_enhanced(text):
    """增强版文本清理"""
    # 标准化Unicode字符
    text = unicodedata.normalize('NFKC', text)

    # 替换各种空白字符
    text = text.replace('\xa0', ' ')  # &nbsp;
    text = text.replace('\u200b', '')  # 零宽度空格
    text = text.replace('\u200e', '')  # 左到右标记
    text = text.replace('\u200f', '')  # 右到左标记

    # 使用正则表达式清理
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)  # 移除控制字符
    text = re.sub(r'\s+', ' ', text)  # 合并多个空格

    return text.strip()


class CsbUtils:
    def __init__(self):
        self.base_url = "https://www.csb.gov.hk"
        # 公务员岗位列表
        self.base_url_query = "https://www.csb.gov.hk/english/admin/pay/952.html"

    async def get_jobs_menu(self) -> dict:
        """获取工作岗位列表"""
        url = f"{self.base_url_query}"
        headers = COMMON_HEADERS.copy()
        headers["Referer"] = url

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        results = await self.extract_jobs_data(html)
                        return results
                    else:
                        logging.error(f"请求失败，状态码: {response.status}")
                        return {}
        except Exception as e:
            logging.exception(f"发生错误: {e}")
            return {}

    async def extract_jobs_data(self, html_content: str) -> dict:
        """
        解析出岗位信息
        Args:
            html_content:

        Returns:

        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # 定位到目标内容
        main_content = soup.find(id="mainContent")
        if not main_content:
            return {}
        # 提取标题
        page_title = clean_text_enhanced(main_content.find('h2').get_text().strip())
        # 提取所有薪资标准链接
        pay_scales = []
        # 从ul列表中提取
        ul = main_content.find('ul')
        if ul:
            for link in ul.find_all('a', href=True):
                title = clean_text_enhanced(link.get_text().strip())
                href = link['href'] if not link['href'].startswith('http') else link['href']
                path = pathlib.Path("/") / href
                url1 = self.base_url + "/" + str(path.resolve().relative_to('/'))
                pay_scales.append({"title": title, "url": url1})

            # 输出结果
            result = {
                "page_title": page_title,
                "base_url": self.base_url,
                "pay_scales": pay_scales
            }
        else:
            result = {}

        return result

    async def find_job_salary_back_markdown(self, job_name: str, job_url: str) -> Dict[str, str]:
        """
        通过岗位名称/代码进行检索

        Args:
            job_name: 岗位名称
            job_url: 薪资岗位的url

        Returns: markdown格式，如果找不到记录返回空

        """
        if not job_name or not job_url:
            return {"query": "", "result": "", "url": ""}

        # 查询岗位薪水的信息
        rs = await self.find_job_salary(job_url)
        url = f"{job_url}"
        if not rs and type(rs) != dict:
            return {"query": job_name, "result": "", "url": url}
        headers = rs["headers"]
        keys = rs["keys"]
        data = rs["data"]

        # 形成markdown文档
        lines = ""
        for row in data:
            m0 = keys[0]
            m1 = keys[1]
            m2 = keys[2]
            lines += f"{m0}: {row[m0]}, {m1}: {row[m1]}, {m2}: {row[m2]}\n"

        markdown = f"""
Title: {job_name}
Headers: {headers}

Data:
{lines}
"""
        return {"query": job_name, "result": markdown, "url": url}

    async def find_job_salary(self, url: str) -> dict:
        """
        通过岗位代码检索岗位的薪资水平

        Args:
            url: 岗位薪水的url

        Returns: markdown格式，如果找不到记录返回空

        """
        # 定义请求头
        headers = COMMON_HEADERS.copy()
        headers["Referer"] = self.base_url_query

        try:
            async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        results = self.extract_salary_data(html)
                        return results
                    else:
                        logging.error(f"请求失败，状态码: {response.status}")
                        return {}
        except Exception as e:
            logging.exception(f"发生错误: {e}")
            return {}

    @staticmethod
    def extract_salary_data(html_content: str):
        """
        按照指定路径提取薪资数据
        """
        # 创建BeautifulSoup对象
        soup = BeautifulSoup(html_content, "html.parser")

        # 定位到目标内容
        main_content = soup.find(id="mainContent")
        if not main_content:
            return {}
        # 提取标题
        title = clean_text_enhanced(main_content.find("h1").get_text().strip())
        # 提取表格数据
        table = main_content.find("table")
        data_list = []
        # 提取表头
        headers = []
        header_rows = table.find_all("tr")[:2]  # 前两行是表头
        for row in header_rows:
            th_elements = row.find_all("th")
            for th in th_elements:
                header_text = th.get_text().strip()
                header_text = clean_text_enhanced(header_text)
                if header_text and header_text not in headers:
                    headers.append(header_text)

        # 提取数据行
        data_rows = table.find_all("tr")[2:]  # 从第三行开始是数据
        m0 = headers[0]
        m1 = headers[1]
        m2 = headers[2]
        for row in data_rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 3:
                point = clean_text_enhanced(cells[0].get_text().strip())
                as_at_3132025 = clean_text_enhanced(cells[1].get_text().strip())
                wef_142025 = clean_text_enhanced(cells[2].get_text().strip())

                data_list.append({
                    m0: point,
                    m1: as_at_3132025,
                    m2: wef_142025
                })

        # 构建最终结果
        result = {
            "title": title,
            "headers": headers,
            "data": data_list,
            "keys": [m0, m1, m2]
        }

        return result


def jobs(is_update: bool = False) -> list:
    """
    获取工作岗位信息

    Args:
        is_update: 是否更新，如果为True将会从拉取最新的记录（慢），否则直接加载已有记录

    Returns:

    """
    try:
        job_menu_path = f"{SCRIPT_ROOT}/jobs_menus.json"
        if is_update:
            # 加载新记录
            job_utils = CsbUtils()
            dic = asyncio.run(job_utils.get_jobs_menu())
            if dic:
                # 更新最新的工作岗位信息
                with open(job_menu_path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(dic))
                return dic["pay_scales"]
        # 加载旧记录
        # 从之前的记录中加载
        with open(job_menu_path, "r", encoding="utf-8") as f:
            s = f.read()
            dic = json.loads(s)
        return dic["pay_scales"]
    except Exception as e:
        logging.exception(f"加载工作岗位异常: {e}")
        return []


def crawl(query: str) -> Dict[str, str]:
    """
    Performs a crawl operation based on the given query string.

    Args:
        query: The search query string to use for crawling.

    Returns:
        A dictionary containing the query, result, and URL.
        e.g., {'query': '...', 'result': '...', 'url': '...'}

    """
    if not query or not query.strip():
        return {"query": query, "result": "", "url": ""}

    # 获取岗位列表
    jobs_menu = jobs()
    if not jobs_menu:
        return {"query": query, "result": "", "url": ""}
    # 匹配出岗位代码和岗位名称
    job_name = ""
    job_url = ""
    for row in jobs_menu:
        if query in row.get("title"):
            job_name = row.get("title")
            job_url = row.get("url")
            break

    # 初始化工具
    job_utils = CsbUtils()

    # 检索岗位的薪资
    rs = asyncio.run(job_utils.find_job_salary_back_markdown(job_name, job_url))
    return rs
