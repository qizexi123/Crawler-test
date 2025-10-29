"""
安装依赖库: pip install beautifulsoup4 'aiohttp[speedups]'
"""
import json

from utils.hurun_utils import jobs, crawl

# 加载工作岗位信息
# is_update默认为False,如果设置为True则进行数据更新（数据来源为对应网站的数据）
jobs_menu = jobs(is_update=True)
print(jobs_menu)

# # 查询查询工作岗位的薪水
# # rs = crawl("胡润百富榜")
# rs = crawl("胡润中国500强")
# print(json.dumps(rs, indent=2, ensure_ascii=False))
# print("result美化效果：")
# print(rs["result"])
