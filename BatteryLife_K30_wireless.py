#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Created by Allen Luo
import configparser
import datetime
import logging
import os
import re
import subprocess
import sys
import threading
import time
import schedule
import uiautomator2 as u2
from dingtalkchatbot.chatbot import DingtalkChatbot

#############
#
# 构建一个实现统计应用程序耗电的程序
# 开启双线程运行，一个线程执行应用程序常规操作，另一个监控当前电量。
# 将测试日志以时间格式命名写进当前目录中，并发送钉钉消息通知测试结束
# 微信，QQ各两个测试账号，实现账号之间信息互发
##############


# 定义一个处理打印日志的方法
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
formatter = logging.Formatter('[%(asctime)s]-[%(name)s]-[%(levelname)s]-%(message)s')
file_time = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
result_root = '{}//'.format(file_time)
if not os.path.exists(result_root):  # 如果目录不存在则创建
    os.makedirs(result_root)
logfile = result_root + '{}.log'.format(file_time)
handler = logging.FileHandler(logfile)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)


def installdependet():
    """
    安装相关测试依赖
    通常情况下python -m uiautomator2 init命令可以帮我们直接安装相关依赖到手机上，但是如果没有联网的话 该命令就无法下载依赖包，现将该命令解析提取出来，手动执行。
    python-uiautomator2 是安卓应用的Java测试框架Uiautomator的一个Python封装。所以uiautomator这个app是一定要装的。但是uiautomator不怎么稳定，需要被照看，
    所以就有了atx-agent这个东西。后来为了使用方便，atx-agent增加远程控制的功能，依赖minicap和minitouch这两个工具,所以说init这个命令往手机上安装的东西一共有
    app-uiautomator.apk
    app-uiautomator-test.apk
    atx-agent
    minicap（可安装）
    minitouch（可安装）
    :return:
    """
    try:
        # os.system('adb -s %s uninstall com.github.uiautomator.test' % devicesid)
        # os.system('adb -s %s uninstall com.github.uiautomator' % devicesid)
        # print("卸载com.github.uiautomator.test、com.github.uiautomator成功")
        cmd1 = 'adb -s %s install -r -t ' % devicesid + os.getcwd() + '\\dependencies\\' + 'app-uiautomator.apk'
        os.system(cmd1)
        print("执行 " + cmd1)

        cmd2 = 'adb -s %s install -r -t ' % devicesid + os.getcwd() + '\\dependencies\\' + 'app-uiautomator-test.apk'
        os.system(cmd2)
        print("执行 " + cmd2)

        cmd3 = 'adb -s %s push ' % devicesid + os.getcwd() + '\\dependencies\\' + 'atx-agent /data/local/tmp/'
        os.system(cmd3)
        print("执行 " + cmd3)

        cmd4 = 'adb -s %s shell chmod 755 /data/local/tmp/atx-agent' % devicesid
        os.system(cmd4)
        print("执行 " + cmd4)

        cmd5 = 'adb -s %s shell /data/local/tmp/atx-agent version' % devicesid
        print("执行 " + cmd5)
        print("当前atx-agent版本 ")
        os.system(cmd5)

        cmd6 = 'adb -s %s shell /data/local/tmp/atx-agent server -d' % devicesid
        os.system(cmd6)
        print("atx-agent已后台运行")
    except BaseException as e:
        print("安装依赖失败" + str(e))


def test_pre():
    # os.popen("adb root")
    # time.sleep(1)
    # os.popen("adb shell content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0")
    # logger.info("已关闭屏幕旋转")
    # time.sleep(1)
    # 使用usb连接电脑，测试开始前模拟执行如下命令，模拟断电，正常耗电。
    # os.system("adb -s %s shell dumpsys battery unplug" %devicesid)
    # 测试开始前重置电量信息
    os.system("adb -s %s shell dumpsys batterystats --reset" % devicesid)
    print('\033[1;40;43m 测试运行中，请谨慎关闭窗口... \033[0m')  # 有高亮
    print('\033[1;40;32m 测试运行中，请谨慎关闭窗口... \033[0m')  # 有高亮
    print('\033[1;31;40m 测试运行中，请谨慎关闭窗口... \033[0m')  # 有高亮


def get_device():
    # 连接手机
    try:
        # 引用Settings文件中的配置项
        logger.info("设备串号：%s" % devicesid)
        if not d.info['screenOn']:  # 监测屏幕是否休眠 如是则解锁点亮屏幕
            os.popen("adb -s %s shell input keyevent 26" % devicesid)
            time.sleep(1)
            d.swipe(0.1, 0.9, 0.9, 0.1)
            time.sleep(1)
        # 开启uiautomator 防止重复启动
        d.uiautomator.start()
        # 如果没有找到设备 10秒后关闭程序
    except BaseException as e:
        logger.error("设备连接异常" + str(e))
        i = 11
        a = 1
        while a < i:
            i = i - 1
            time.sleep(1)
            print("%s 秒后将关闭窗口" % i)
        sys.exit()


def get_battery():
    """
    定义该方法获取当前测试设备的电池电量
    写死红米K30电池容量为5000毫安时
    通过电池电量损耗判断是否退出程序
    :return:
    """
    cmd = "adb -s %s shell dumpsys battery" % devicesid
    out_count = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE).stdout.readlines()
    for line in out_count:
        line_ = line.decode('utf-8').strip()
        # 构建一个正则表达式获取电量信息，输出电池容量Capacity及消耗电量drain
        # re.findall匹配出的结果为一个列表，会输出空列表
        battery_level = re.findall('level: (.*)', line_)
        # 获取列表不为空的数据
        if len(battery_level) != 0:
            ramian_eletric = "".join(battery_level)  # 将列表字符串重新连接为新的字符串
            logger.info("测试开始时电量百分比:{}".format(before_test_eletric))
            print("测试开始时电量百分比:{}".format(before_test_eletric))
            logger.info("剩余电量百分比:{}".format((ramian_eletric)))
            print("剩余电量百分比:{}".format((ramian_eletric)))
            # 获取测试结束时间
            end_time1 = datetime.datetime.now()
            # 计算耗时
            expend_time = end_time1 - k30_start_time
            logger.info("已测试时间： %s" % (str(expend_time).split('.')[0]))
            print("已测试时间：{}".format((str(expend_time).split('.')[0])))
            # 判断耗剩余电量百分比是否小于等于1
            if float(ramian_eletric) <= float(1):
                # 将电池信息格式化输出
                b = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
                os.system("adb -s %s shell dumpsys batterystats > %sbatterystats.txt" % (devicesid, b))
                logger.info("电池数据已下载")
                os.system("adb -s %s  shell dumpsys meminfo > %smeminfo.txt" % (devicesid, b))
                logger.info("内存数据已下载")
                # 导出测试结束时进程信息
                os.system("adb -s %s shell ps >  %sps.txt" % (devicesid, b))
                logger.info("进程数据已下载")
                # 获取测试结束时间
                end_time = datetime.datetime.now()
                logger.info("结束测试时间： %s" % (str(end_time).split('.')[0]))
                # 计算耗时
                expend_time = end_time - k30_start_time
                logger.info("总共耗时： %s" % (str(expend_time).split('.')[0]))
                # 测试结束后模拟恢复供电
                # os.system("adb -s %s shell dumpsys battery reset" % devicesid)
                # logger.info("已供电")
                logger.info("--------**测试结束**--------")
                d.press("home")  # 回到桌面
                # WebHook地址
                webhook = 'https://oapi.dingtalk.com/robot/send?access_token' \
                          '=c66c89841b4e36bb93409238cdbd2dc25fb791aae95a8637a8ed717f3372783a '
                # 初始化机器人小丁
                xiaoding = DingtalkChatbot(webhook)
                # 通知指定的用户
                at_mobiles = ['13530195722']
                # 测试结束Markdown消息@指定用户
                xiaoding.send_text(msg='K30脱线续航测试结束！耗时：' + (str(expend_time).split('.')[0]), at_mobiles=at_mobiles,
                                   is_at_all=False)
                time.sleep(2)
                os.system("adb -s %s bugreport" % devicesid)
                logger.info("bugreport已下载")
                sys.exit()



def getstart_time():
    """
    获取测试开始时间
    :return:
    """
    global k30_start_time
    k30_start_time = datetime.datetime.now()
    logger.info("开始测试时间： %s" % (str(k30_start_time).split('.')[0]))


def aiqiyitest(logger):
    # 引用Settings文件中的配置项
    # 设备信息
    d = u2.connect_usb(devicesid)
    time.sleep(2)
    # 获取测试开始时间
    start_time = datetime.datetime.now()
    logger.info("爱奇艺开始时间： %s" % (str(start_time).split('.')[0]))
    a = time.time()
    b = a
    while b - a < 600:  # 设置运行时间大于 b - a 时跳出循环,其中b - a单位是秒
        try:
            if not d.info['screenOn']:  # 监测屏幕是否休眠 如是则解锁点亮屏幕
                os.popen("adb -s %s shell input keyevent 26" % devicesid)
                time.sleep(1)
                d.swipe(0.1, 0.9, 0.9, 0.1)
            d.press("home")
            # 打开微博
            d.app_start("com.qiyi.video")
            logger.info("启动了爱奇艺")
            time.sleep(10)
            # 必须要运行监测器
            d.watcher.run()
            # 必须要运行监测器
            d.watcher('Permission_a').when('我知道了').click()
            d.watcher('Permission_b').when("com.qiyi.video:id/dialog_close").click()
            d.watcher('Permission_b').when("com.qiyi.video:id/unused_res_a").click()
            d.watcher('Permission_i').when('不了，谢谢').click()
            d.watcher('Permission').when('暂不升级').click()  # 如果出现以后再说点击

            # 点击搜索框
            d.click(0.488, 0.074)
            time.sleep(1)
            logger.info("输入楚乔传搜索")
            # 输入楚乔传并搜索
            d(focused=True).set_text("楚乔传")
            d(text="搜索").click()
            time.sleep(2)
            d.click(0.103, 0.392)
            logger.info("开始播放第一集")
            time.sleep(2)
            if (d(text="继续播放").exists):
                d(text="继续播放").click()
            i = 0
            while i < 10:
                d.swipe(500, 1800, 500, 1000)
                time.sleep(30)
                d.swipe(500, 1000, 500, 1800)
                time.sleep(30)
                i += 1
            c = time.time()
            b = c

        except Exception as e:
            logger.error("爱奇艺元素定位出错！" + str(e))
            d.app_stop("com.qiyi.video")
            c = time.time()
            b = c
    logger.info("10分钟播放结束")
    d.press("back")
    time.sleep(2)
    d.press("back")
    time.sleep(2)
    d.press("back")
    time.sleep(1)
    d.press("home")

    end_time = datetime.datetime.now()
    logger.info("本轮爱奇艺结束时间： %s" % (str(end_time).split('.')[0]))
    expend_time = end_time - start_time
    logger.info("本轮爱奇艺总共耗时：%s" % ( str(expend_time).split('.')[0]))



def camertest(logger):
    # 设备信息
    d = u2.connect_usb(devicesid)
    time.sleep(2)
    # 获取测试开始时间
    start_time = datetime.datetime.now()
    logger.info("相机开始时间： %s" % (str(start_time).split('.')[0]))
    a = time.time()
    b = a
    while b - a < 600:  # 设置运行时间大于 b - a 时跳出循环,其中b - a单位是秒
        try:
            if not d.info['screenOn']:  # 监测屏幕是否休眠 如是则解锁点亮屏幕
                os.popen("adb -s %s shell input keyevent 26" % devicesid)
                time.sleep(1)
                d.swipe(0.1, 0.9, 0.9, 0.1)
                time.sleep(2)
            d.app_start("com.android.camera")
            logger.info("打开相机应用")
            # 暂停
            time.sleep(5)
            # 点击拍照按钮（后置摄像头）
            d(resourceId="com.android.camera:id/v9_shutter_button_internal").click()
            logger.info("点击了后置拍照")

            time.sleep(5)
            # 点击图库按钮
            d.click(0.206, 0.841)
            logger.info("切换到了图库")
            # 图片放大缩小 两指从坐标（x,y） (m,n)移动到（a,b） (c,d)
            time.sleep(2)

            d().gesture((0.317, 0.333), (0.779, 0.673), (0.385, 0.425), (0.504, 0.509))
            logger.info("缩放图片")
            # 返回
            time.sleep(5)
            # 切换到前摄像头
            d(resourceId="com.android.camera:id/v9_camera_picker").click()
            logger.info("切换到了前置摄像头")

            time.sleep(5)
            # 点击拍照按钮（前置摄像头）
            d(resourceId="com.android.camera:id/v9_shutter_button_internal").click()
            logger.info("点击了拍照")
            time.sleep(5)
            # 点击图库按钮
            d.click(0.235, 0.834)
            logger.info("切换到了图库")
            time.sleep(2)

            # 图片放大缩小 两指从坐标（x,y） (m,n)移动到（a,b） (c,d)
            d().gesture((0.317, 0.333), (0.779, 0.673), (0.385, 0.425), (0.504, 0.509))
            logger.info("缩放图片")
            time.sleep(5)
            # 返回前置摄像头
            d(resourceId="com.android.camera:id/v9_camera_picker").click()
            time.sleep(5)

        except Exception as e:
            logger.error("相机元素定位出错！" + str(e))
            d.app_stop("com.android.camera")
            pass
        c = time.time()
        b = c
        time.sleep(2)
        d.press("home")
    end_time = datetime.datetime.now()
    logger.info("本轮相机结束时间： %s" % (str(end_time).split('.')[0]))
    expend_time = end_time - start_time
    logger.info("本轮相机总共耗时：%s" % (str(expend_time).split('.')[0]))


def dialer(logger):
    # 引用Settings文件中的配置项
    # 设备信息
    d = u2.connect_usb(devicesid)
    time.sleep(2)
    # 获取测试开始时间
    start_time = datetime.datetime.now()
    logger.info("拨号开始时间： %s" % (str(start_time).split('.')[0]))
    a = time.time()
    b = a
    while b - a < 300:  # 设置运行时间大于 b - a 时跳出循环,其中b - a单位是秒
        try:
            if not d.info['screenOn']:  # 监测屏幕是否休眠 如是则解锁点亮屏幕
                os.popen("adb -s %s shell input keyevent 26" % devicesid)
                time.sleep(1)
                d.swipe(0.1, 0.9, 0.9, 0.1)
                time.sleep(2)
            d.press("home")  # 回到桌面
            # 进入拨号界面
            d.app_start("com.android.contacts")
            logger.info("打开了拨号")
            time.sleep(5)
            d(text="通话").click()
            time.sleep(2)
            logger.info("开始拨打112")

            d.click(0.16, 0.548)
            time.sleep(1)
            d.click(0.16, 0.55)
            time.sleep(1)
            d.click(0.525, 0.547)
            time.sleep(1)
            d(resourceId="com.android.contacts:id/single_call_container").click()
            # d.click(0.486, 0.873)
            time.sleep(30)
            d(resourceId="com.android.incallui:id/endButton").click()

            # d.click(0.551, 0.768)
            logger.info("结束拨打112")
            time.sleep(5)

        except Exception as e:
            logger.error("dialer元素定位出错！" + str(e))
            d.app_start("com.android.contacts")

        c = time.time()
        b = c
        time.sleep(5)
        d.press("home")

    end_time = datetime.datetime.now()
    logger.info("本轮拨号结束时间： %s" % (str(end_time).split('.')[0]))
    expend_time = end_time - start_time
    logger.info("本轮拨号总共耗时：%s" % (str(expend_time).split('.')[0]))



def douyin(logger):
    # 设备信息
    d = u2.connect_usb(devicesid)
    time.sleep(2)
    # 获取测试开始时间
    start_time = datetime.datetime.now()
    logger.info("抖音开始时间： %s" % (str(start_time).split('.')[0]))
    a = time.time()
    b = a
    while b - a < 600:  # 设置运行时间大于 b - a 时跳出循环,其中b - a单位是秒
        try:
            if not d.info['screenOn']:  # 监测屏幕是否休眠 如是则解锁点亮屏幕
                os.popen("adb -s %s shell input keyevent 26" % devicesid)
                time.sleep(1)
                d.swipe(0.1, 0.9, 0.9, 0.1)
                time.sleep(2)
            d.press("home")  # 回到桌面
            # 进入抖音界面
            d.app_start("com.ss.android.ugc.aweme")
            logger.info("打开了抖音")
            time.sleep(10)
            d.watcher.run()

            # 必须要运行监测器
            d.watcher('Permission_c').when('好的').click()
            d.watcher('Permission_d').when('以后再说').click()
            d.watcher('Permission_j').when('我知道了').click()
            d.watcher('Permission_k').when('稍后').click()
            d.watcher('Permission_l').when('取消').click()
            # d.watcher("Permission_c").watched = True
            # d.watcher("Permission_d").watched = True
            # d.watcher("Permission_j").watched = True
            # d.watcher("Permission_k").watched = True
            # d.watcher("Permission_l").watched = True

            d(text="关注").click()
            logger.info("点击了关注")
            time.sleep(15)
            logger.info("开始下滑操作")
            # 滑动操作
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)

        except Exception as e:
            logger.error("抖音元素定位出错！" + str(e))
            d.app_stop("com.ss.android.ugc.aweme")
        c = time.time()
        b = c
        time.sleep(1)
        d.press("home")
    end_time = datetime.datetime.now()
    logger.info("本轮抖音结束时间： %s" % (str(end_time).split('.')[0]))
    expend_time = end_time - start_time
    logger.info("本轮抖音总共耗时：%s" % (str(expend_time).split('.')[0]))



def qqtest(logger):
    # 设备信息
    d = u2.connect_usb(devicesid)
    time.sleep(2)
    # 获取测试开始时间
    start_time = datetime.datetime.now()
    logger.info("QQ开始时间： %s" % (str(start_time).split('.')[0]))
    a = time.time()
    b = a
    while b - a < 600:  # 设置运行时间大于 b - a 时跳出循环,其中b - a单位是秒
        try:
            if not d.info['screenOn']:  # 监测屏幕是否休眠 如是则解锁点亮屏幕
                os.popen("adb -s %s shell input keyevent 26" % devicesid)
                time.sleep(1)
                d.swipe(0.1, 0.9, 0.9, 0.1)
                time.sleep(2)
            # 启用qq
            d.app_start("com.tencent.mobileqq")
            logger.info("打开了QQ")

            time.sleep(5)
            # 点击联系人
            d.click(0.38, 0.90)
            # d.xpath('//*[@text="联系人"]').click()
            time.sleep(2)
            # 点击我的好友
            d(text="群聊").click()
            time.sleep(2)
            d(resourceId="com.tencent.mobileqq:id/text1").click()
            time.sleep(1)
            d(resourceId="com.tencent.mobileqq:id/input").click()
            time.sleep(1)
            # d(resourceId="com.tencent.mobileqq:id/txt", text="发消息").click()
            # 点击发送消息 输入文字
            d.set_fastinput_ime(True)
            time.sleep(1)
            d(focused=True).set_text("RedMi_K30续航测试123ABC")
            time.sleep(1)
            d.set_fastinput_ime(False)
            time.sleep(2)
            # 点击发送按钮
            d(resourceId="com.tencent.mobileqq:id/fun_btn").click()
            logger.info("发送了文字")
            time.sleep(2)
            # 选择图片功能
            d.click(0.244, 0.598)
            time.sleep(2)
            # 选中前一张图片（如照片为横屏拍摄，通过坐标点击会不准，改用使用className定位方式）
            d(className='android.widget.CheckBox').click()
            time.sleep(2)
            # 点击发送按钮
            d(resourceId="com.tencent.mobileqq:id/send_btn").click()
            logger.info("发送了图片")
            time.sleep(2)
            # 返回上一个页面
            d.press("back")
            time.sleep(2)
            d.press("back")
            # 返回主页面
            time.sleep(2)
            d.press("home")

        except Exception as e:
            logger.error("QQ元素定位出错！" + str(e))
            d.app_stop("com.tencent.mobileqq")

        c = time.time()
        b = c
        time.sleep(1)

    end_time = datetime.datetime.now()
    logger.info("本轮QQ结束时间： %s" % (str(end_time).split('.')[0]))
    expend_time = end_time - start_time
    logger.info("本轮QQ总共耗时：%s" % (str(expend_time).split('.')[0]))



def taobaortest(logger):
    # 设备信息
    d = u2.connect_usb(devicesid)
    time.sleep(2)
    # 获取测试开始时间
    start_time = datetime.datetime.now()
    logger.info("淘宝开始时间： %s" % (str(start_time).split('.')[0]))
    a = time.time()
    b = a
    while b - a < 600:  # 设置运行时间大于 b - a 时跳出循环,其中b - a单位是秒
        try:
            if not d.info['screenOn']:  # 监测屏幕是否休眠 如是则解锁点亮屏幕
                os.popen("adb -s %s shell input keyevent 26" % devicesid)
                time.sleep(1)
                d.swipe(0.1, 0.9, 0.9, 0.1)
            time.sleep(2)
            d.press("home")  # 回到桌面
            # 启动淘宝
            d.app_start("com.taobao.taobao")
            logger.info("启动了淘宝")
            # 暂等待10秒
            time.sleep(10)
            d.watcher.run()

            d.watcher('Permission_e').when('取消').click()
            d.watcher('Permission_f').when('允许').click()
            d.watcher('Permission_g').when("关闭").click()
            # d.watcher("Permission_e").watched = True
            # d.watcher("Permission_f").watched = True
            # d.watcher("Permission_g").watched = True

            logger.info("开始搜索")
            # 定位搜索框
            d(description="搜索").click()
            time.sleep(2)
            d(resourceId="com.taobao.taobao:id/searchEdit").click()
            time.sleep(2)
            # 输入女鞋搜索
            d(resourceId="com.taobao.taobao:id/searchEdit").send_keys("女鞋")
            time.sleep(2)
            logger.info("开始搜索女鞋")
            # 点击搜索按钮
            d(resourceId="com.taobao.taobao:id/searchbtn").click()
            time.sleep(5)
            logger.info("开始滑动")
            # 滑动操作
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)



      # 定位搜索框
            d(resourceId="com.taobao.taobao:id/searchEdit").click()
            d.clear_text()
            time.sleep(2)
            logger.info("开始搜索女装")
            d(resourceId="com.taobao.taobao:id/searchEdit").send_keys("女装")
            # 点击搜索按钮
            d(resourceId="com.taobao.taobao:id/searchbtn").click()
            time.sleep(5)
            # 滑动操作
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)

            # 定位搜索框
            d(resourceId="com.taobao.taobao:id/searchEdit").click()
            d.clear_text()
            time.sleep(2)
            logger.info("开始搜索女包")
            d(resourceId="com.taobao.taobao:id/searchEdit").send_keys("女包")
            # 点击搜索按钮
            d(resourceId="com.taobao.taobao:id/searchbtn").click()
            time.sleep(5)
            # 滑动操作
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)

            # 定位搜索框
            d(resourceId="com.taobao.taobao:id/searchEdit").click()
            d.clear_text()
            time.sleep(2)
            logger.info("开始搜索女裤")
            d(resourceId="com.taobao.taobao:id/searchEdit").send_keys("女裤")
            # 点击搜索按钮
            d(resourceId="com.taobao.taobao:id/searchbtn").click()
            time.sleep(5)
            logger.info("开始滑动")
            # 滑动操作
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)
            d.press("back")
            time.sleep(1)
            d.press("back")
            time.sleep(1)
            d.press("back")
        except Exception as e:
            logger.error("淘宝元素定位出错！" + str(e))
            d.app_stop("com.taobao.taobao")
        c = time.time()
        b = c
        time.sleep(1)
        d.press("home")

    end_time = datetime.datetime.now()
    logger.info("本轮淘宝结束时间： %s" % (str(end_time).split('.')[0]))
    expend_time = end_time - start_time
    logger.info("本轮淘宝总共耗时：%s" % ( str(expend_time).split('.')[0]))



def toutiao(logger):
    # 设备信息
    d = u2.connect_usb(devicesid)
    time.sleep(2)
    # 获取测试开始时间
    start_time = datetime.datetime.now()
    logger.info("今日头条开始时间： %s" % (str(start_time).split('.')[0]))
    a = time.time()
    b = a
    while b - a < 600:  # 设置运行时间大于 b - a 时跳出循环,其中b - a单位是秒
        try:
            if not d.info['screenOn']:  # 监测屏幕是否休眠 如是则解锁点亮屏幕
                os.popen("adb -s %s shell input keyevent 26" % devicesid)
                time.sleep(1)
                d.swipe(0.1, 0.9, 0.9, 0.1)
                time.sleep(1)
            d.press("home")
            # 打开微博
            d.app_start("com.ss.android.article.news")
            logger.info("启动了今日头条")
            time.sleep(10)
            d.watcher.run()
            d.watcher('Permission_a').when('允许').click()
            d.watcher('Permission_i').when('不了，谢谢').click()
            d.watcher('Permission').when('以后再说').click()  # 如果出现以后再说点击
            d.click(0.935, 0.135)
            time.sleep(2)
            # 点击热点栏目
            d.click(0.373, 0.16)
            # d(text="关注").click()
            time.sleep(10)
            logger.info("开始滑动热点栏目")
            d.swipe(500, 1500, 500, 500)
            time.sleep(10)
            d.swipe(500, 1500, 500, 500)
            time.sleep(10)
            d.swipe(500, 500, 500, 1500)
            time.sleep(10)
            d.swipe(500, 500, 500, 1500)
            time.sleep(10)
            d.click(0.935, 0.135)
            time.sleep(2)
            # 点击本地
            d.click(0.626, 0.16)
            # d(text="推荐").click()
            time.sleep(10)
            logger.info("开始滑动本地栏目")
            d.swipe(500, 1500, 500, 500)
            time.sleep(10)
            d.swipe(500, 1500, 500, 500)
            time.sleep(10)
            d.swipe(500, 500, 500, 1500)
            time.sleep(10)
            d.swipe(500, 500, 500, 1500)
            time.sleep(10)

            c = time.time()
            b = c

        except Exception as e:
            logger.error("今日头条元素定位出错！" + str(e))
            d.app_stop("com.ss.android.article.news")
            c = time.time()
            b = c
    logger.info("今日头条新闻浏览结束")
    time.sleep(1)
    d.press("home")

    end_time = datetime.datetime.now()
    logger.info("本轮今日头条结束时间： %s" % (str(end_time).split('.')[0]))
    expend_time = end_time - start_time
    logger.info("本轮今日头条总共耗时：%s" % ( str(expend_time).split('.')[0]))



def wangzherongyaotest(logger):
    # 设备信息
    d = u2.connect_usb(devicesid)
    time.sleep(2)
   # 获取测试开始时间
    start_time = datetime.datetime.now()
    logger.info("王者荣耀开始时间： %s" % (str(start_time).split('.')[0]))
    a = time.time()
    b = a
    while b - a < 300:  # 设置运行时间大于 b - a 时跳出循环,其中b - a单位是秒
        try:
            if not d.info['screenOn']:  # 监测屏幕是否休眠 如是则解锁点亮屏幕
                os.popen("adb -s %s shell input keyevent 26" % devicesid)
                time.sleep(1)
                d.swipe(0.1, 0.9, 0.9, 0.1)
                time.sleep(2)
            d.app_start('com.tencent.tmgp.sgame')
            logger.info("启动王者荣耀")
            time.sleep(30)
        except Exception as e:
            logger.error("王者荣耀元素定位出错！"  + str(e))
            d.app_stop('com.tencent.tmgp.sgame')

        c = time.time()
        b = c
        time.sleep(2)
        d.app_stop('com.tencent.tmgp.sgame')

    end_time = datetime.datetime.now()
    logger.info("本轮王者荣耀结束时间： %s" % (str(end_time).split('.')[0]))
    expend_time = end_time - start_time
    logger.info("本轮王者荣耀总共耗时：%s" % (str(expend_time).split('.')[0]))


def wechattest(logger):
    # 设备信息
    d = u2.connect_usb(devicesid)
    time.sleep(2)
    # 获取测试开始时间
    start_time = datetime.datetime.now()
    logger.info("微信开始时间： %s" % (str(start_time).split('.')[0]))
    a = time.time()
    b = a
    while b - a < 600:  # 设置运行时间大于 b - a 时跳出循环,其中b - a单位是秒
        try:
            if not d.info['screenOn']:  # 监测屏幕是否休眠 如是则解锁点亮屏幕
                os.popen("adb -s %s shell input keyevent 26" % devicesid)
                time.sleep(1)
                d.swipe(0.1, 0.9, 0.9, 0.1)
                time.sleep(2)
            d.press("home")
            # 启动微信
            d.app_start("com.tencent.mm")
            logger.info("启动了微信")
            # 暂停
            time.sleep(5)
            # 点击微信
            d.click(0.12, 0.901)
            time.sleep(2)
            # 点击通讯录
            d.click(0.364, 0.901)
            time.sleep(2)
            logger.info("点击通讯录")
            d(text='群聊').click()
            time.sleep(2)
            d(text="gelitest").click()
            logger.info("点击了群聊")
            time.sleep(1)
            # 点击输入框
            d.click(0.482, 0.898)
            d.set_fastinput_ime(True)
            time.sleep(1)
            d(focused=True).set_text("RedMi_K30续航测试123ABC")
            time.sleep(1)
            d.set_fastinput_ime(False)
            time.sleep(1)
            # 点击发送按钮
            d(text='发送').click()
            logger.info("发送了文字")
            time.sleep(1)
            # 点击+号
            d(className="android.widget.ImageButton", descriptionContains="更多功能按钮").click()
            # d(resourceId="com.tencent.mm:id/aqi").click()
            time.sleep(1)
            # 选择相册按钮
            d(text="相册").click()
            time.sleep(1)
        #   选择图片
            d(className='android.widget.CheckBox').click()
            time.sleep(1)
            # 通过发送按钮文本字样定位
            d(text='发送(1/9)').click()
            logger.info("发送了图片")

            time.sleep(1)
            # 定位到语音输入按钮
            d(className="android.widget.ImageButton", descriptionContains="切换到按住说话").click()
            time.sleep(1)
            # d(resourceId="com.tencent.mm:id/aqa").click()
            # 点击“按住说话”按钮3秒
            d(description='按住说话').long_click(3)
            logger.info("发送了语音")
            # d(resourceId="com.tencent.mm:id/aqd").long_click(3)
            time.sleep(1)
            d(descriptionContains = "切换到键盘").click()
            time.sleep(1)
            # 返回到上一界面
            d.press("back")
            time.sleep(2)
            d.press("back")
            time.sleep(2)
            # 定位到发现
            d.click(0.511, 0.897)
            time.sleep(2)
            # 定位到朋友圈
            d(text='朋友圈').click()
            logger.info("开始浏览朋友圈")
            time.sleep(15)
            # 滑动操作
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)
            # 返回到主界面
            d.press("back")

            time.sleep(2)
            # 返回到桌面
            d.press("home")
        except Exception as e:
            logger.error("微信元素定位出错！" + str(e))
            d.app_stop("com.tencent.mm")

        c = time.time()
        b = c
        time.sleep(2)
        d.press("home")

    end_time = datetime.datetime.now()
    logger.info("本轮微信结束时间： %s" % (str(end_time).split('.')[0]))
    expend_time = end_time - start_time
    logger.info("本轮微信总共耗时：%s" % (str(expend_time).split('.')[0]))


def weibotest(logger):
    # 设备信息
    d = u2.connect_usb(devicesid)
    time.sleep(2)
    # 获取测试开始时间
    start_time = datetime.datetime.now()
    logger.info("微博开始时间： %s" % (str(start_time).split('.')[0]))
    a = time.time()
    b = a
    while b - a < 600:  # 设置运行时间大于 b - a 时跳出循环,其中b - a单位是秒
        try:
            if not d.info['screenOn']:  # 监测屏幕是否休眠 如是则解锁点亮屏幕
                os.popen("adb -s %s shell input keyevent 26" % devicesid)
                time.sleep(1)
                d.swipe(0.1, 0.9, 0.9, 0.1)
                time.sleep(2)
            d.press("home")
            # 打开微博
            d.app_start("com.sina.weibo")
            logger.info("启动了微博")
            time.sleep(10)
            d.watcher.run()

            d.watcher('Permission_b').when("com.sina.weibo:id/iv_close").click()
            d.watcher('Permission_i').when('不了，谢谢').click()
            d.watcher('Permission').when('以后再说').click()  # 如果出现以后再说点击
            # d.watcher("Permission_b").watched = True
            # d.watcher("Permission_i").watched = True
            # d.watcher("Permission").watched = True
            # 启动方法1：后台启动，持续监控
            # d.watchers.watched = True
            # 启动方法2：只启动一次
            # d.watchers.run()
            # 点击关注
            d.click(0.57, 0.067)
            time.sleep(1)
            d.click(0.41, 0.067)
            logger.info("点击了关注")
            time.sleep(2)
            # d.press("back")
            # time.sleep(2)
            logger.info("开始上下滑动")
            # 滑动操作
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)
            d.press("home")

        except Exception as e:
            logger.error("微博元素定位出错！" + str(e))
            d.app_stop("com.sina.weibo")
        c = time.time()
        b = c
        time.sleep(1)
        d.press("home")

    end_time = datetime.datetime.now()
    logger.info("本轮微博结束时间： %s" % (str(end_time).split('.')[0]))
    expend_time = end_time - start_time
    logger.info("本轮微博总共耗时：%s" % ( str(expend_time).split('.')[0]))


def browser(logger):
    # 设备信息
    d = u2.connect_usb(devicesid)
    time.sleep(2)
    # 获取测试开始时间
    start_time = datetime.datetime.now()
    logger.info("浏览器结束时间： %s" % (str(start_time).split('.')[0]))
    a = time.time()
    b = a
    while b - a < 600:  # 设置运行时间大于 b - a 时跳出循环,其中b - a单位是秒
        try:
            if not d.info['screenOn']:  # 监测屏幕是否休眠 如是则解锁点亮屏幕
                os.popen("adb -s %s shell input keyevent 26" % devicesid)
                time.sleep(1)
                d.swipe(0.1, 0.9, 0.9, 0.1)
                time.sleep(2)
            d.press("home")  # 回到首页
            # 进入格力定制版UC浏览器
            d.app_start("com.android.browser")
            logger.info("打开浏览器")
            time.sleep(5)
            # 点击百度小图标
            d(text="人民网").click()
            logger.info("开始人民网新闻浏览")
            time.sleep(5)
            logger.info("开始上下滑动操作")
            # 滑动操作
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 1500, 500, 500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)
            d.swipe(500, 500, 500, 1500)
            time.sleep(15)
            logger.info("结束人民网新闻浏览")
            # 返回上一层
            d.press('back')
            time.sleep(5)
            # 停止程序运行
            d.press("home")

        except Exception as e:
            logger.error("浏览器元素定位出错！"+ str(e))
            d.app_stop("com.UCMobile.gree")
            pass
        c = time.time()
        b = c
        time.sleep(1)
        d.press('back')
        time.sleep(5)
        d.press("home")

    end_time = datetime.datetime.now()
    logger.info("本轮浏览器结束时间： %s" % (str(end_time).split('.')[0]))
    expend_time = end_time - start_time
    logger.info("本轮浏览器总共耗时：%s" % (str(expend_time).split('.')[0]))



def sleep_awake():
    """
    定义一个睡眠之后唤醒的方法，通过发送url -x 命令启动uiautomator进程
    防止休眠之后uiautomator被结束进程，唤醒不起来
    :return:
    """
    try:
        time.sleep(2)
        d.press('power')  # 熄屏
        logger.info("5分钟熄屏开始")
        time.sleep(5 * 60)
        if not d.screen_on():
            os.popen("adb -s %s shell input keyevent 26" % devicesid)
        time.sleep(1)
        d.swipe(0.1, 0.9, 0.9, 0.1)
        # os.popen("adb -s %s shell input keyevent 82" % devicesid)
        time.sleep(1)
        d.press("home")
        logger.info("5分钟熄屏结束")
        time.sleep(2)
    except Exception as e:
        logger.error("休眠唤醒失败" + str(e))
        os.popen("adb -s %s shell input keyevent 26" % devicesid)
        time.sleep(1)
        d.swipe(0.1, 0.9, 0.9, 0.1)
        time.sleep(1)
        d.press("home")


def run_test():
    """
    定义run_test运行应用程序，执行常规操作
    :return:
    """
    n = 1
    while True:
        aiqiyitest(logger)
        logger.info("--------**第%s轮爱奇艺结束**--------" % n)
        time.sleep(5)

        douyin(logger)
        logger.info("--------**第%s轮抖音结束**--------" % n)
        time.sleep(5)

        camertest(logger)
        logger.info("--------**第%s轮相机结束**--------" % n)
        time.sleep(5)

        dialer(logger)
        logger.info("--------**第%s轮拨号结束**--------" % n)
        time.sleep(5)

        sleep_awake()

        taobaortest(logger)
        logger.info("--------**第%s轮淘宝结束**--------" % n)
        time.sleep(5)

        browser(logger)
        logger.info("--------**第%s轮浏览器结束**--------" % n)
        time.sleep(5)

        qqtest(logger)
        logger.info("--------**第%s轮QQ结束**--------" % n)
        time.sleep(5)

        sleep_awake()

        wangzherongyaotest(logger)
        logger.info("--------**第%s轮王者荣耀结束**--------" % n)
        time.sleep(5)

        weibotest(logger)
        logger.info("--------**第%s轮微博结束**--------" % n)
        time.sleep(5)

        wechattest(logger)
        logger.info("--------**第%s轮微信结束**--------" % n)
        time.sleep(5)

        toutiao(logger)
        logger.info("--------**第%s轮头条结束**--------" % n)
        time.sleep(5)

        sleep_awake()

        logger.info("--------**第%s轮测试结束**--------" % n)
        n += 1


def screen_light():
    """
   设置常亮亮度为2048
   K30的亮度最大值为4096
   将亮度条拉倒最大执行adb shell settings get system screen_brightness所得最大亮度值
    :return:
    """

    try:
        logger.info("将手机自动亮度调节功能关闭")
        os.popen("adb -s %s shell settings put system screen_brightness_mode 0" % devicesid)
        time.sleep(1)
        logger.info("设置常亮亮度为2048")
        # light = cf.get("screenbrightnessConf", "screenbrightness")
        # os.popen("adb -s %s shell settings put system screen_brightness %s" % (devicesid, light))
        os.popen("adb -s %s shell settings put system screen_brightness 2048" % devicesid)
    except Exception as e:
        logger.error("设置亮度出错" + str(e))
        d.press("home")


def set_audio():
    """
    设置媒体音量值为0
    根据adb shell media volume --get 获取最大音量值为15
    :return:
    """
    try:
        # audio = cf.get("VolumeConf", "Volume")
        # os.popen("adb -s %s shell media volume --set %s" %(devicesid, audio))
        # logger.info("已将%s音量值设置为 %s\n"  %(devicesid, audio))
        os.popen("adb -s %s shell media volume --set 0" % devicesid)
        logger.info("已将%s音量值设置为 0\n" % devicesid)
    except Exception as e:
        logger.error("设置音量出错" + str(e))
        d.press("home")


def get_adb():
    '''
    获取连接的设备号
    :return:
    '''
    cmd = "adb devices"
    out_content = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE).stdout.read().decode('utf-8')
    devices = re.findall('(.*)device', out_content)
    try:
        devices.remove('List of ')
        if devices:
            for index in devices:
                index.replace('\t', '').replace('\n', '')
                devices_list = [index.replace('\t', '').replace('\n', '') for index in devices]
                return devices_list
        else:
            return "检测到当前没有连接设备，请插入设备后重试！"
    except:
        return []


if __name__ == "__main__":
    #############
    # 执行多线程操作
    #############
    # file_path = './GCconfig.ini'
    # cf = configparser.ConfigParser()  # configparser类来读取config文件
    # cf.read(file_path)
    print("待测试设备串号，序号如下：")
    devices = get_adb()[:]
    if devices == '检测到当前没有连接设备，请插入设备后重试！':
        print("检测到当前没有连接设备，请插入设备后重试！")
        print("3秒后程序退出！")
        time.sleep(3)
        sys.exit()
    for i in devices:
        print("序号：%s   设备串号：%s" % (devices.index(i) + 1, i))
    device_num = input("请输入待测试设备的数字序号，如1： ")
    if device_num.isdigit() is False:
        print("输入的非数字，请检查")
        print("==================程序退出================")
        time.sleep(5)
        sys.exit()
    elif device_num < str(1):
        print("输入的数字序号不在待测试数字序号范围内，请重试")
        print("==================程序退出================")
        time.sleep(5)
        sys.exit()
    elif device_num > str(len(devices)):
        print("输入的数字序号不在待测试数字序号范围内，请重试")
        print("==================程序退出================")
        time.sleep(5)
        sys.exit()
    devicesid = get_adb()[:][int(device_num) - 1]
    d = u2.connect_usb(devicesid)

    installdependet()
    test_pre()
    get_device()
    screen_light()
    set_audio()

    cmd1 = "adb -s %s shell dumpsys battery" % devicesid
    out_count = subprocess.Popen(cmd1, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE).stdout.readlines()
    for line in out_count:
        line_ = line.decode('utf-8').strip()
        # 构建一个正则表达式获取电量信息，输出电池容量Capacity及消耗电量drain
        # re.findall匹配出的结果为一个列表，会输出空列表
        battery_level = re.findall('level: (.*)', line_)
        # 获取列表不为空的数据
        if len(battery_level) != 0:
            before_test_eletric = "".join(battery_level)  # 将列表字符串重新连接为新的字符串

    getstart_time()
    threading.Thread(target=get_battery, args=()).start()
    threading.Thread(target=run_test, args=(), daemon=True).start()  # 设置daemon守护线程 随着主线程的退出而退出
    schedule.every(5).seconds.do(get_battery)  # 每2秒刷新一下获取电量
    while True:
        schedule.run_pending()