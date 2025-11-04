"""
https://open.tianyancha.com/ 官方api调用工具集
"""
import asyncio
import datetime
import json
import logging
import pathlib
from typing import Dict

import aiofiles
import aiohttp

# token
TOKEN = "e2d7ffea-5a24-4db8-87ac-9992b55151d5"
# 脚本所在目录
SCRIPT_ROOT = pathlib.Path(__file__).parent

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
COMMON_HEADERS = {
    "User-Agent": USER_AGENT,
    'Authorization': TOKEN,  # token验证信息
}


class TianYanChaAPIUtils:
    def __init__(self):
        # api基础路径
        self.base_url = "https://open.api.tianyancha.com"
        # 核对基础路径
        self.view_base_url = "https://www.tianyancha.com/company"

    async def find_by_company_back_markdown(self, keyword: str, load_test=False) -> Dict[str, str]:
        """
        查询公司的基本信息

        Args:
            keyword: 搜索关键字（公司名称、公司id、注册号或社会统一信用代码）
            load_test: 是否加载测试数据

        Returns: markdown格式，如果找不到记录返回空

        """
        if not load_test:
            # 查询公司的前置信息
            dic = await self.find_by_company(keyword)
            if not dic:
                return {"query": keyword, "result": "", "url": ""}
        else:
            async with aiofiles.open(f"{SCRIPT_ROOT}/../temps/test_data.json", encoding="utf-8") as f:
                s = await f.read()
                dic = json.loads(s)
        error_code = dic.get("error_code")
        if error_code != 0:
            logging.warning(f"请求接口错误: {error_code}) {dic['reason']}")
            return {"query": keyword, "result": "", "url": ""}
        basic_info = dic.get("result")
        if not basic_info or type(basic_info) != dict:
            return {"query": keyword, "result": "", "url": ""}
        cid = basic_info.get('id', '--')
        cname = basic_info.get('historyNames', '--').split(";")[0]
        try:
            cdt = datetime.datetime.fromtimestamp(basic_info.get('estiblishTime')).strftime("%Y-%m-%d")
        except Exception:
            cdt = "--"
        try:
            fdt = datetime.datetime.fromtimestamp(basic_info.get('fromTime')).strftime("%Y-%m-%d")
        except Exception:
            fdt = "--"
        try:
            edt = datetime.datetime.fromtimestamp(basic_info.get('toTime')).strftime("%Y-%m-%d")
        except Exception:
            edt = "无固定期限"
        lines = f"企业名称: {cname}; 英文名称: {basic_info.get('property3', '--')}" + "\n"
        lines += f"公司代码: {basic_info.get('bondNum', '--')}" + "\n"
        lines += f"法定代表人: {basic_info.get('percentileScore', '--')}; 企业状态: {basic_info.get('regStatus', '--')}" + "\n"
        lines += f"企业评分: {basic_info.get('percentileScore', '--')}; 成立日期: {cdt}" + "\n"
        lines += f"统一社会信用代码: {basic_info.get('creditCode', '--')}; 注册资本: {basic_info.get('regCapital', '--')}; 实缴资本: {basic_info.get('actualCapital', '--')}" + "\n"
        lines += f"工商注册号: {basic_info.get('regNumber', '--')}; 纳税人识别号: {basic_info.get('taxNumber', '--')}; 组织机构代码: {basic_info.get('orgNumber', '--')}" + "\n"
        lines += f"营业期限: {fdt}至{edt}" + "\n"
        lines += f"企业类型: {basic_info.get('companyOrgType', '--')}; 行业: {basic_info.get('industry', '--')}; 人员规模: {basic_info.get('staffNumRange', '--')}" + "\n"
        lines += f"参保人数: {basic_info.get('socialStaffNum', '--')}" + "\n"
        lines += f"登记机关: {basic_info.get('regInstitute', '--')}; 注册地址: {basic_info.get('regLocation', '--')};" + "\n"
        lines += f"经营范围: {basic_info.get('businessScope', '--')}" + "\n"

        markdown = f"""
# {cname} 公司信息

{lines}
"""
        return {"query": keyword, "result": markdown, "url": f"{self.view_base_url}/{cid}"}

    async def find_by_company(self, keyword: str) -> dict:
        """
        通过公司名称、公司id、注册号或社会统一信用代码进行检索

        Args:
            keyword: 搜索关键字（公司名称、公司id、注册号或社会统一信用代码）

        Returns: markdown格式，如果找不到记录返回空

        """
        # 定义请求头
        headers = COMMON_HEADERS
        params = {"keyword": keyword}
        # 构建目标url
        url = f"{self.base_url}/services/open/ic/baseinfoV2/2.0"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        dic = await response.json()
                        return dic
                    else:
                        print(f"请求失败，状态码: {response.status}")
                        return {}
        except Exception as e:
            logging.exception(f"发生错误: {e}")
            return {}


def crawl(query: str, load_test: bool = False) -> Dict[str, str]:
    """
    Performs a crawl operation based on the given query string.

    Args:
        query: The search query string to use for crawling.
        load_test: If set to True, enables load testing mode, Defaults to False for normal operation.

    Returns:
        A dictionary containing the query, result, and URL.
        e.g., {'query': '...', 'result': '...', 'url': '...'}

    """
    if not query or not query.strip():
        return {"query": query, "result": "", "url": ""}

    # 初始化工具
    cn_utils = TianYanChaAPIUtils()

    # 查询公司信息
    rs = asyncio.run(cn_utils.find_by_company_back_markdown(query, load_test))

    return rs
