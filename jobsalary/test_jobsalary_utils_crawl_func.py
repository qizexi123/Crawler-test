"""
安装依赖库: pip install beautifulsoup4 'aiohttp[speedups]'
"""
from utils.jobsalary_utils import jobs, crawl

# # 加载工作岗位信息
# jobs_menu = jobs()
# print(jobs_menu)

# 查询查询工作岗位的平均薪资
# rs = crawl("隨扈／安全人員")
# rs = crawl("經營管理主管")
rs = crawl("營建工程人員")
print(rs)
