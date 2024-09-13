import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import json
from PIL import Image
from io import BytesIO
import base64


# 要抢的课程
courses_wanted = ['DCS5234']



with open('account.json', 'r') as file:
    account = json.load(file)

netid = account['netid']
pwd = account['pwd']
access_token = account['access_token']

os.environ['NO_PROXY'] = '*'

service = Service(executable_path='./chromedriver-mac-arm64/chromedriver')
driver = webdriver.Chrome(service=service)

# 1. 选课登陆
driver.get('https://cms.sysu.edu.cn/#/login')

login_button = WebDriverWait(driver, 3).until(
    EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/div/div[2]/div[2]/div[1]/div[3]/div[1]/div[2]/button'))
)
login_button.click()

# 2. 中央身份服务
cas_domain = driver.current_url.split('//')[1].split('/')[0]
new_domain = cas_domain
cas_first_try = True
while new_domain == cas_domain:
    multi_try_mod = 0 if cas_first_try else 1
    
    # /html/body/div/div[1]/div/div[2]/div[1]/form/div[2]/div/input
    netid_input = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.XPATH, f'/html/body/div/div[1]/div/div[2]/div[1]/form/div[{1+multi_try_mod}]/div/input'))
    )
    
    # /html/body/div/div[1]/div/div[2]/div[1]/form/div[3]/input
    pwd_input = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.XPATH, f'/html/body/div/div[1]/div/div[2]/div[1]/form/div[{2+multi_try_mod}]/input'))
    )
    
    # /html/body/div/div[1]/div/div[2]/div[1]/form/div[4]/input
    captcha_input = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.XPATH, f'/html/body/div/div[1]/div/div[2]/div[1]/form/div[{3+multi_try_mod}]/input'))
    )
    
    # /html/body/div/div[1]/div/div[2]/div[1]/form/section[2]/input[4]
    login_button_cas = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.XPATH, '/html/body/div/div[1]/div/div[2]/div[1]/form/section[2]/input[4]'))
    )

    # 填写netid和密码
    netid_input.send_keys(netid)
    pwd_input.send_keys(pwd)

    # 二维码识别
    # /html/body/div/div[1]/div/div[2]/div[1]/form/div[4]/img
    captcha_image = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.XPATH, f'/html/body/div/div[1]/div/div[2]/div[1]/form/div[{3+multi_try_mod}]/img'))
    )
    captcha_image_x, captcha_image_y = captcha_image.location.values()
    captcha_image_h, captcha_image_w = captcha_image.size.values()
    screenshot = driver.get_screenshot_as_png()
    screenshot = Image.open(BytesIO(screenshot))
    # MAC系统因为二倍率截图，需要*2，其他系统去掉即可
    captcha_image_screenshot = screenshot.crop((captcha_image_x * 2, captcha_image_y * 2, (captcha_image_x + captcha_image_w) * 2, (captcha_image_y + captcha_image_h) * 2))
    # 使用百度OCR识别验证码
    captcha_buffer = BytesIO()
    captcha_image_screenshot.save(captcha_buffer, 'PNG')
    captcha_str = captcha_buffer.getvalue()
    captcha_buffer.close()
    captcha_base64 = base64.b64encode(captcha_str).decode('utf-8')
    # req_url = f'https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}'
    req_url = f'https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token={access_token}'
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    response = requests.post(req_url, data={"image": captcha_base64}, headers=headers)
    captcha_answer = response.json()['words_result'][0]['words']
    captcha_input.send_keys(captcha_answer)
    login_button_cas.click()
    
    new_domain = driver.current_url.split('//')[1].split('/')[0]
    cas_first_try = False


# 3. 课程管理系统
select_course_button = WebDriverWait(driver, 3).until(
    EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/section/div/main/div/div[1]/div[1]/div/div/div[2]/div/div/div[1]/a'))
)
select_course_button.click()


# 4. 选课界面
# driver切换到新tab
all_handles = driver.window_handles
new_handle = all_handles[-1]
driver.switch_to.window(new_handle)


while True:
    # 滚动屏幕
    cms_html_height = driver.execute_script('return document.documentElement.scrollHeight')
    cms_html_height_next = None
    while cms_html_height != cms_html_height_next:
        cms_html_height = driver.execute_script('return document.documentElement.scrollHeight')
        driver.execute_script(
            'document.documentElement.scrollTop = document.documentElement.scrollHeight'
        )
        time.sleep(1)
        cms_html_height_next = driver.execute_script('return document.documentElement.scrollHeight')

        
    # 课程列表
    course_ul = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div/div[2]/div/div[1]/div/div[2]/div[3]/div/div/div[2]/div/ul'))
    )
    course_li_list = course_ul.find_elements(By.TAG_NAME, 'li')

    for course_wanted in courses_wanted:
        for course_li in course_li_list:
            course_title = course_li.find_element(By.XPATH, ".//div[@class='stu-xk-bot-con-title2']/div[1]").text
            course_code = course_title.split('-')[0]
            # print(course_title)
            # print(course_code)
            
            if course_code == course_wanted:
                # 遍历到想选的那门课
                registration_button = course_li.find_element(By.XPATH, ".//div[@class='stu-xk-bot-r-unfiltrate']/button[@class='ant-btn ant-btn-primary ant-btn-background-ghost']")
                course_selected = False
                button_text = registration_button.find_element(By.XPATH, './span').text
                if button_text == '选 课':
                    course_selected = False
                elif button_text == '退 课':
                    course_selected = True
                else:
                    raise ValueError(f'course_selected = {course_selected}')
                
                free_count = int(course_li.find_element(By.XPATH, "./div[2]/div[3]/p[2]").text)
                print(f'{course_title} 剩余空位：{free_count}')
                
                if free_count > 0 and not course_selected:
                    # registration_button.click()
                    print(f'{course_title}已点击')

    # 刷新屏幕
    driver.refresh()
    time.sleep(2)


driver.quit()
