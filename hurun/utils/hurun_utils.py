"""
https://www.hurun.net/ 工具
"""
import asyncio
import json
import logging
import pathlib
from typing import Dict

import aiohttp
from aiohttp import ClientTimeout

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
COMMON_HEADERS = {
    "User-Agent": USER_AGENT,
    # "Referer": "https://www.jobsalary.com.tw/"
}
SCRIPT_ROOT = pathlib.Path(__file__).parent
TIMEOUT = ClientTimeout(total=300)


class CsbUtils:
    def __init__(self):
        # 百富榜：浏览器端
        self.view_url = "https://www.hurun.net/zh-CN/Rank/HsRankDetails?pagetype={page_type}"
        # 百富榜：前20榜单，可以调整offset和limit实现加载更多
        # search: %E4%BB%BB%E6%AD%A3%E9%9D%9E => 任正非，支持检索
        self.base_url_query = "https://www.hurun.net/zh-CN/Rank/HsRankDetailsList?num={num}&search=&offset=0&limit=20"

    @staticmethod
    async def get_rankings_names() -> list:
        """获取各个榜单名称列表"""
        lis = [
            {"page_type": "rich", "num": "ODQWW2BI", "name": "胡润百富榜单"},  # 胡润百富榜单
            {"page_type": "ctop500", "num": "Y7SPAAYO", "name": "胡润中国500强榜单"},  # 胡润中国500强榜单
        ]
        return lis

    async def find_rankings_back_markdown(self, page_type: str, num: str, name: str) -> Dict[str, str]:
        """
        查询相关榜单信息

        Args:
            page_type: 访问的页面类型
            num: 加载数据的编码
            name: 榜单的名称

        Returns: markdown格式，如果找不到记录返回空

        """
        if not page_type or not num or not name:
            return {"query": "", "result": "", "url": ""}

        # 查询岗位薪水的信息
        rs = await self.find_rankings(num)
        url = self.view_url.format(page_type=page_type)
        if not rs and type(rs) != dict:
            return {"query": name, "result": "", "url": url}

        # 形成markdown文档
        lines = ""
        if page_type == "rich":
            # 百富榜
            titles = ["排名", "财富(￥)", "排名变化", "个人信息", "企业信息"]
            lines += ",".join(titles) + "\n"
            for row in rs:
                male_str = row["hs_Character"][0]["hs_Character_Gender"]
                age_str = row["hs_Character"][0]["hs_Character_Age"] + "岁"
                line = [
                    str(row["hs_Rank_Rich_Ranking"]),
                    str(row["hs_Rank_Rich_Wealth"]),
                    str(row["hs_Rank_Rich_Ranking_Change"]),
                    row["hs_Rank_Rich_ChaName_Cn"] + " " + male_str + " " + age_str,
                    row["hs_Rank_Rich_Industry_Cn"] + " 行业：" + row["hs_Rank_Rich_Industry_Cn"],
                ]
                lines += (",".join(line)).replace("\n", " ") + "\n"
        elif page_type == "ctop500":
            # 中国500强
            titles = ["排名", "企业估值(￥)", "企业信息", "CEO", "行业"]
            lines += ",".join(titles) + "\n"
            for row in rs:
                line = [
                    str(row["hs_Rank_CTop500_Ranking"]),
                    str(row["hs_Rank_CTop500_Wealth"]),
                    row["hs_Rank_CTop500_ComName_Cn"],
                    row["hs_Rank_CTop500_ChaName_Cn"],
                    row["hs_Rank_CTop500_Industry_Cn"],
                ]
                lines += ",".join(line).replace("\n", " ") + "\n"
        else:
            return {"query": name, "result": "", "url": url}

        markdown = f"""
# {name}

{lines}
"""
        return {"query": name, "result": markdown, "url": url}

    async def find_rankings(self, num: str) -> list:
        """
        通过num来查询对应的榜单

        Args:
            num: 榜单编码

        Returns: markdown格式，如果找不到记录返回空

        """
        # 定义请求头
        headers = COMMON_HEADERS.copy()
        url = self.base_url_query.format(num=num)

        try:
            async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        dic = await response.json()
                        return dic["rows"]
                    else:
                        logging.error(f"请求失败，状态码: {response.status}")
                        return []
        except Exception as e:
            logging.exception(f"发生错误: {e}")
            return []


def jobs(is_update: bool = False) -> list:
    """
    获取工作岗位信息

    Args:
        is_update: 是否更新，如果为True将会从拉取最新的记录（慢），否则直接加载已有记录

    Returns:

    """
    try:
        rankings_names_path = f"{SCRIPT_ROOT}/rankings_names.json"
        if is_update:
            # 加载新记录
            job_utils = CsbUtils()
            lis = asyncio.run(job_utils.get_rankings_names())
            if lis:
                # 更新最新的工作岗位信息
                with open(rankings_names_path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(lis))
                return lis
        # 加载旧记录
        # 从之前的记录中加载
        with open(rankings_names_path, "r", encoding="utf-8") as f:
            s = f.read()
            lis = json.loads(s)
        return lis
    except Exception as e:
        logging.exception(f"加载榜单信息异常: {e}")
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
    rankings_names = jobs()
    if not rankings_names:
        return {"query": query, "result": "", "url": ""}
    # 匹配出岗位代码和岗位名称
    page_type = ""
    num = ""
    name = ""
    for row in rankings_names:
        # {"page_type": "rich", "num": "ODQWW2BI", "name": "胡润百富榜单"}
        if query in row.get("name") or query in row.get("page_type") or query in row.get("num"):
            page_type = row.get("page_type")
            num = row.get("num")
            name = row.get("name")
            break

    # 初始化工具
    job_utils = CsbUtils()

    # 检索岗位的薪资
    rs = asyncio.run(job_utils.find_rankings_back_markdown(page_type, num, name))
    return rs
