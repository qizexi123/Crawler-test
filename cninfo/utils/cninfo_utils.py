"""
www.cninfo.com.cn 工具
"""
import asyncio
import json
import logging
import random
from typing import Dict
from urllib.parse import quote

import aiohttp

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
COMMON_HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://www.cninfo.com.cn/"
}


class CNInfoUtils:
    def __init__(self):
        # 静态资源路径
        self.base_url_static = "https://static.cninfo.com.cn"

        # 公司的检索：支持公司名称、公司代码
        self.base_url_cquery = "https://www.cninfo.com.cn/new/information/topSearch/detailOfQuery"
        # 公司检索：公司的简介
        self.base_url_company_profile = "https://www.cninfo.com.cn/data20/companyOverview/getCompanyIntroduction?scode="
        # 公司检索：公司的高管信息
        self.base_url_company_executive = "https://www.cninfo.com.cn/data20/companyOverview/getCompanyExecutives?scode="
        # 公司检索：公司的公告
        self.base_url_company_news = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
        # 给用户核对数据用
        self.base_url_company_for_human = "https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={s_code}#companyProfile"

        # 公司高管检索：人名
        self.base_url_uquery = "https://www.cninfo.com.cn/new/executive/recommend"
        self.base_url_user_for_human = "https://www.cninfo.com.cn/new/fulltextSearch?notautosubmit=&keyWord={username}&searchType=0"

    async def find_by_company_back_markdown(self, keyword: str) -> Dict[str, str]:
        """
        通过公司名称/代码进行检索

        Args:
            keyword: 公司名称、公司编码、公司高管名称等

        Returns: markdown格式，如果找不到记录返回空

        """
        # 查询公司的前置信息
        rs = await self.find_by_company(keyword)
        if not rs:
            # print("error: find_by_company_back_markdown-1")
            return {"query": keyword, "result": "", "url": ""}
        dic = json.loads(rs)
        key_board_list = dic.get("keyBoardList")
        if not key_board_list or type(key_board_list) != list:
            # print("error: find_by_company_back_markdown-2")
            return {"query": keyword, "result": "", "url": ""}
        s_code = key_board_list[0].get("code")
        org_id = key_board_list[0].get("orgId", "")
        s_name = key_board_list[0].get("zwjc", "")
        url = self.base_url_company_for_human.format(org_id=org_id, s_code=s_code)
        if not s_code:
            # print("error: find_by_company_back_markdown-3")
            return {"query": keyword, "result": "", "url": url}

        # 随机休眠一下，避免被限制
        await asyncio.sleep(random.randint(3, 5))

        # 1. 查询公司的简介信息
        result = await self.get_company_profile(s_code)
        if not result:
            # print("error: find_by_company_back_markdown-4")
            return {"query": keyword, "result": "", "url": url}
        records = result.get('data', {}).get('records')
        if not records:
            # print("error: find_by_company_back_markdown-5")
            return {"query": keyword, "result": "", "url": url}
        basic_info = records[0].get("basicInformation")
        list_info = records[0].get("listingInformation")
        if not basic_info:
            # print("error: find_by_company_back_markdown-6")
            return {"query": keyword, "result": "", "url": url}
        basic_info = basic_info[0]
        if list_info:
            list_info = list_info[0]
        else:
            list_info = {}
        lines = f"公司名称: {basic_info.get('ORGNAME', '--')}; 英文名称: {basic_info.get('F001V', '--')}" + "\n"
        lines += f"公司简称: {basic_info.get('ASECNAME', '--')}; 公司代码: {basic_info.get('ASECCODE', '--')}" + "\n"
        lines += f"曾用简称: {basic_info.get('F002V', '--')}; 关联证券: {basic_info.get('BSECNAME', '--')}" + "\n"
        lines += f"所属市场: {basic_info.get('MARKET', '--')}; 所属行业: {basic_info.get('F032V', '--')}" + "\n"
        lines += f"成立日期: {basic_info.get('F010D', '--')}; 上市日期: {basic_info.get('F006D', '--')}" + "\n"
        lines += f"法人代表: {basic_info.get('F003V', '--')}; 总经理: {basic_info.get('F042V', '--')}" + "\n"
        lines += f"公司董秘: {basic_info.get('F018V', '--')}; 邮政编码: {basic_info.get('F006V', '--')}" + "\n"
        lines += f"注册地址: {basic_info.get('F004V', '--')}; 办公地址: {basic_info.get('F005V', '--')}" + "\n"
        lines += f"联系电话: {basic_info.get('F013V', '--')}; 传真: {basic_info.get('F014V', '--')}" + "\n"
        lines += f"官方网址: {basic_info.get('F011V', '--')}; 电子邮箱: {basic_info.get('F012V', '--')}" + "\n"
        lines += f"每股面值(元): {list_info.get('F007N', '--')}; 首发价格(元): {list_info.get('F008N', '--')}" + "\n"
        lines += f"首发募资净额(万元): {list_info.get('F028N', '--')}" + "\n"
        lines += f"首发主承销商: {list_info.get('F047V', '--')}" + "\n"
        lines += f"入选指数: {basic_info.get('F044V', '--')}" + "\n"
        lines += f"主营业务: {basic_info.get('F015V', '--')}" + "\n"
        lines += f"经营范围: {basic_info.get('F016V', '--')}" + "\n"
        lines += f"机构简介: {basic_info.get('F017V', '--')}" + "\n"

        # 随机休眠一下，避免被限制
        await asyncio.sleep(random.randint(3, 5))

        # 2. 查询公司的高管
        result = await self.get_company_executives(s_code)
        if not result:
            # print("error: find_by_company_back_markdown-7")
            return {"query": keyword, "result": "", "url": url}
        records = result.get('data', {}).get('records')
        if not records:
            # print("error: find_by_company_back_markdown-8")
            return {"query": keyword, "result": "", "url": url}
        title_map = {
            "姓名": "F002V",
            "职务": "F009V",
            "学历": "F017V",
            "年薪(万元)": "F005N",
            "持股数(股)": "F012N",
        }
        title_lis = ["姓名", "职务", "学历", "年薪(万元)", "持股数(股)"]
        title_str = "|".join(title_lis)
        split_str = "|".join(["----"] * len(title_lis))
        contents1 = []
        for i, row in enumerate(records, 1):
            content = []
            for k in title_lis:
                key = title_map.get(k)
                val = row.get(key, "--")
                if not val or val in ["null", "None"]:
                    val = "--"
                content.append(str(val))
            contents1.append("|" + "|".join(content) + "|")
        contents1_str = "\n".join(contents1)
        # 随机休眠一下，避免被限制
        await asyncio.sleep(random.randint(3, 5))

        # 3. 获取公司的新闻
        result = await self.get_company_news(f"{s_code},{org_id}")
        if not result or not result.get("announcements", []):
            news_str = ""
        else:
            announcements = result.get("announcements", [])
            news_str = ""
            for row in announcements[:3]:
                news_str += f"{row.get('announcementTitle')}, url为: {self.base_url_static}/{row.get('adjunctUrl')}" + "\n"

        markdown = f"""
# {s_name} 公司信息

## 公司简介
{lines}

## 公司高管
|{title_str}|
|{split_str}|
{contents1_str}

## 公司公告
{news_str}
"""
        return {"query": keyword, "result": markdown, "url": url}

    async def find_by_username_back_markdown(self, username: str) -> Dict[str, str]:
        """
        通过高管姓名进行检索

        Args:
            username: 高管姓名

        Returns: str 成功返回markdown内容，否则返回空

        """
        rs = await self.find_by_username(username)
        url = self.base_url_user_for_human.format(username=quote(username))
        if not rs:
            return {"query": username, "result": "", "url": url}
        dic = json.loads(rs)
        docs = dic.get("docs")
        if not docs or type(docs) != list:
            return {"query": username, "result": "", "url": url}

        title_map = {
            "股票代码": "stockcode",
            "股票简称": "stockname",
            "现价": "",
            "涨跌幅": "",
            "高管名称": "humanname",
            "职务": "job",
            "在任状态": "status",
        }
        title_lis = ["序号", "股票代码", "股票简称", "现价", "涨跌幅", "高管名称", "职务", "在任状态"]
        title_str = "|".join(title_lis)
        split_str = "|".join(["----"] * len(title_lis))
        contents = []
        for i, row in enumerate(docs, 1):
            content = [str(i)]
            for k in title_lis:
                # 跳过序号
                if k == "序号":
                    continue
                key = title_map.get(k)
                val = row.get(key, "")
                if key == "status":
                    if val:
                        val = "在职"
                    else:
                        val = "离职"
                content.append(val)
            contents.append("|" + "|".join(content) + "|")
        contents_str = "\n".join(contents)

        markdown = f"""
# {username} 担任的高管信息

|{title_str}|
|{split_str}|
{contents_str}
"""
        # return markdown
        return {"query": username, "result": markdown, "url": url}

    async def find_by_company(self, keyword: str) -> str:
        """
        通过公司名称/代码进行检索

        Args:
            keyword: 公司名称、公司编码、公司高管名称等

        Returns: markdown格式，如果找不到记录返回空

        """
        # 定义请求头
        headers = COMMON_HEADERS
        # 创建 FormData 对象
        form = aiohttp.FormData()
        form.add_field("keyWord", keyword)
        form.add_field("maxSecNum", 10)
        form.add_field("maxListNum", 5)
        # 构建目标url
        url = f"{self.base_url_cquery}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=form) as response:
                    if response.status == 200:
                        html = await response.text()
                        return html
                    else:
                        print(f"请求失败，状态码: {response.status}")
                        return ""
        except Exception as e:
            logging.exception(f"发生错误: {e}")
            return ""

    async def find_by_username(self, keyword: str) -> str:
        """
        通过高管名称进行检索

        Args:
            keyword: 高管名称

        Returns: markdown格式，如果找不到记录返回空

        """
        # 定义请求头
        headers = COMMON_HEADERS
        # 创建 FormData 对象
        form = aiohttp.FormData()
        form.add_field("name", keyword)
        # 构建目标url
        url = f"{self.base_url_uquery}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=form) as response:
                    if response.status == 200:
                        html = await response.text()
                        return html
                    else:
                        print(f"请求失败，状态码: {response.status}")
                        return ""
        except Exception as e:
            logging.exception(f"发生错误: {e}")
            return ""

    async def get_company_executives(self, s_code: str) -> dict:
        """
        获取公司高管信息

        Args:
            s_code: 股票代码，如 '000001'
        """
        # 定义请求头
        headers = COMMON_HEADERS
        # 构建目标url
        url = f"{self.base_url_company_executive}{s_code}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        print(f"请求失败，状态码: {response.status}")
                        return {}
        except Exception as e:
            logging.exception(f"发生错误: {e}")
            return {}

    async def get_company_profile(self, s_code: str) -> dict:
        """
        获取公司简介信息

        Args:
            s_code: 股票代码，如 '000001'
        """
        # 定义请求头
        headers = COMMON_HEADERS
        # 构建目标url
        url = f"{self.base_url_company_profile}{s_code}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        print(f"请求失败，状态码: {response.status}")
                        return {}
        except Exception as e:
            logging.exception(f"发生错误: {e}")
            return {}

    async def get_company_news(self, s_code: str) -> dict:
        """
        获取公司新闻

        Args:
            s_code: 股票代码，如 '000001'
        """
        # 定义请求头
        headers = COMMON_HEADERS
        # 创建 FormData 对象
        form = aiohttp.FormData()
        form.add_field("stock", s_code)
        form.add_field("tabName", "fulltext")
        form.add_field("pageSize", 30)
        form.add_field("pageNum", 1)
        form.add_field("column", "szse")
        form.add_field("plate", "sz")
        form.add_field("isHLtitle", True)
        # 定义url
        url = self.base_url_company_news

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=form) as response:
                    if response.status == 200:
                        dic = await response.json()
                        return dic
                    else:
                        print(f"请求失败，状态码: {response.status}")
                        return {}
        except Exception as e:
            logging.exception(f"发生错误: {e}")
            return {}


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

    # 初始化工具
    cn_utils = CNInfoUtils()

    # 1. 优先查询公司信息
    rs = asyncio.run(cn_utils.find_by_company_back_markdown(query))
    if rs and rs.get("result") and rs.get("result").strip():
        return rs

    # 2. 查询高管的信息
    rs = asyncio.run(cn_utils.find_by_username_back_markdown(query))
    return rs
