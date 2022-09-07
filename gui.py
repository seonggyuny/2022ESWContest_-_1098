#gui 구성 라이브러리
from tkinter import *
from tkinter import messagebox

#버스api 구성 라이브러리
import requests, xmltodict, json
import pandas as pd

#qr 구성 라이브러리
from imutils.video import VideoStream
from pyzbar import pyzbar
import argparse
import datetime
import imutils
import time
import cv2

#firebase 구성 라이브러리
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import threading
import copy

# 키오스크 설치 장소 고정
qr_stationId="203000066" #버스정류장, 아주대아주대병원
stationId="203000066" #버스정류장, 아주대아주대병원

# SeatCnt 함수의 전역 변수 배열
rows = 10 # 임의로 정한 버스 최대 갯수
cols = 2
arr = [[0 for j in range(cols)] for i in range(rows)]

#Firebase 생성
cred = credentials.Certificate("/home/pineapple/Downloads/test.json") #경로
firebase_admin.initialize_app(cred, {
'projectId': 'qrkiosk-6963d',
})
db = firestore.client()

# 정렬 함수
def center(toplevel):
    toplevel.update_idletasks()
    w = toplevel.winfo_screenwidth()
    h = toplevel.winfo_screenheight()
    size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
    x = w / 2 - size[0] / 2
    y = h / 2 - size[1] / 2
    toplevel.geometry("%dx%d+%d+%d" % (size + (x, y)))

# QR CODE 함수
def QrCode():
    flag=0
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", type=str, default="barcodes.csv",
        help="path to output CSV file containing barcodes")
    args = vars(ap.parse_args())
    
    # 비디오 스트림 초기화 및 카메라 센서가 예열되도록 함
    vs = VideoStream(src=0).start()                 # USB 웹캠 카메라 
    time.sleep(1.0)
    
    # 작성을 위해 출력된 CSV 파일을 열고, 지금까지 찾은 qr코드 세트 초기화
    csv = open(args["output"], "w")
    found = set()
    
    # 지속적으로 비디오 스트림 받아옴
    while True:
        frame = vs.read()
        frame = cv2.resize(frame, dsize=(800, 480))
        # 프레임에서 qr코드를 찾고, 각 코드들 마다 디코드
        qrcodes = pyzbar.decode(frame)
    
        for qrcode in qrcodes: 
            # 이미지에서 코드의 경계를 직사각형으로 그리고, 이를 추출한다.
            (x, y, w, h) = qrcode.rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
    
            # 코드 데이터는 바이트 객체이므로, 어떤 출력 이미지에 그리려면 가장 먼저 문자열로 변환해야 한다.
            qrcodeData = qrcode.data.decode("utf-8")
            qrcodeType = qrcode.type
    
            # 이미지에서 코드 데이터와 테입(유형)을 그린다.
            text = "{} ({})".format(qrcodeData, qrcodeType)
            cv2.putText(frame, text, (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    
            # 현재 코드 텍스트가 CSV 파일 안에 없을경우, timestamp, qrcode를 작성하고 업데이트
            if qrcodeData not in found:
                csv.write("{},{}\n".format(datetime.datetime.now(),
                    qrcodeData))
                csv.flush()
                found.add(qrcodeData)
            # 현재 코드 텍스트가 CSV파일 안에 있을 경우, flag를 1로 바꾸고 안쪽 반복문 탈출
            else:
                time.sleep(1.0)
                flag=1
                break
                
                # output frame
        cv2.imshow("Qrcode Scanner", frame)
        key = cv2.waitKey(1) & 0xFF
        
        # flag=1인 경우, 바깥쪽 반복문까지 탈출
        if(flag==1):
            break

    # 창닫기
    csv.close()
    cv2.destroyAllWindows()
    vs.stop()
    qr_BusCheck(text)

# FIREBASE 함수
def Firebase_DB(phone, bus, predictTime, locationNo, remainSeatCnt, plateNo, startpoint, endpoint, routeId, stationSeq):
    doc_ref = db.collection('users').document(phone) ###variable!
    doc_ref.set({
        'keyword' : bus,  
        'predictTime1' : predictTime,
        'locationNo1' : locationNo,
        'remainSeatCnt1' : remainSeatCnt,
        'plateNo1' : plateNo,   
        'startpoint' : startpoint,
        'endpoint' : endpoint,
    })

    doc_ref2 = db.collection('users api').document(phone) #각 버스의 좌석 저장
    doc_ref2.set({
        'keyword' : bus,  
        'plateNo1' : plateNo,   
        'routeId' : routeId,
        'stationSeq' : stationSeq,
        'startpoint' : startpoint,
        'endpoint' : endpoint,
    })

def Firebase_update():
    users_ref = db.collection('users api')
    docs = users_ref.stream()

    for doc in docs:
        userqr = doc.id
        userbus_num = doc.get('keyword')
        userbus_origin = doc.get('plateNo1')
        userbus_routeId = doc.get('routeId')
        userbus_stationSeq = doc.get('stationSeq')
        startpoint = doc.get('startpoint')
        endpoint = doc.get('endpoint')

        serviceKey2='HQ7hhajrugx1f30ZP1IGJRkrv%2BLP7qKZVr9I1H%2FmweDkbNracDylSVzVGgOGmKccDF2g%2F%2BivtsCLldfp3QBg%2FQ%3D%3D'
        url3="http://apis.data.go.kr/6410000/busarrivalservice/getBusArrivalItem?serviceKey={}&stationId={}&routeId={}&staOrder={}".format(serviceKey2,qr_stationId,userbus_routeId,userbus_stationSeq)

        content = requests.get(url3).content # GET요청
        dict=xmltodict.parse(content) # XML을 dictionary로 파싱
        
        # 도착예정버스가 없을때를 검사하기
        jsonString = json.dumps(dict['response']['msgHeader'], ensure_ascii=False)
        jsonObj = json.loads(jsonString) # json을 dict으로 변환
        if(jsonObj['resultCode'] != '0'):
            Firebase_DB(userqr, "X", "0", "0", "0", "X", "X", "X", "0", "0") ## 확인
            continue

        jsonString = json.dumps(dict['response']['msgBody']['busArrivalItem'], ensure_ascii=False) # dict을 json으로 변환
        jsonObj = json.loads(jsonString) # json을 dict으로 변환

        update_predictTime1 = StringVar()
        update_locationNo1 = StringVar()
        update_remainSeatCnt1 = StringVar()
        update_plateNo1 = StringVar()

        update_predictTime1 = jsonObj['predictTime1']
        update_locationNo1 = jsonObj['locationNo1']
        update_remainSeatCnt1 = jsonObj['remainSeatCnt1']
        update_plateNo1 = jsonObj['plateNo1']

        # 예약한 버스가 지나갔는지 확인
        if(update_plateNo1 == userbus_origin):
            Firebase_DB(userqr, userbus_num, update_predictTime1, update_locationNo1, update_remainSeatCnt1, update_plateNo1, startpoint, endpoint, userbus_routeId, userbus_stationSeq)
            continue
        else:
            Firebase_DB(userqr, "X", "0", "0", "0", "X", "X", "X", "0", "0")
            j=0
            while(1): #예약한 버스 arr 2열 0으로
                if (arr[j][0]==int(userbus_num)):
                    arr[j][1] = 0
                    break
                else :
                    j += 1
                
                if (j>rows):
                    break
            continue

    time.sleep(30)
    Firebase_update()

# 버스 좌석 확인 함수
def SeatCnt(bus, remainSeatCnt): 
    int_bus=int(bus) #비교를 위해

    i=0
    while(1):

        if(i>rows):
            break

        if(arr[i][0]==0): #null이라면 
            arr[i][0]=int_bus # arr에 새로운 버스번호 추가
            arr[i][1]=1 #cnt시작
            break #그리고 반복문 탈출

        if(arr[i][0] == int_bus): # 이미 추가한 버스가 있다면
            arr[i][1] = arr[i][1] +1
            if(arr[i][1]>int(remainSeatCnt)):
                msgbox2 = messagebox.showerror('에러','남은 좌석이 없습니다. 다른 버스를 예약해주십시오.')
                arr[i][1] = arr[i][1] -1
                break
            break
        i += 1

# 키보드 생성 함수
def KeyBoard(frame, txt):
    def button_clicked(number):
        current = txt.get()
        txt.delete(0, END)
        txt.insert(0, str(current) + str(number))

    def button_clicked_str():
        current = txt.get()
        txt.delete(0, END)
        txt.insert(0, str(current) + "예약")

    def button_clear():
        txt.delete(len(txt.get())-1,'end')

    btn7 = Button(frame,text='7', padx=15, pady=10,command=lambda: button_clicked(7))
    btn7.grid(column=0, row=0, padx=5, pady=5)
    btn8 = Button(frame,text='8', padx=15, pady=10, command=lambda: button_clicked(8))
    btn8.grid(column=1, row=0, padx=5, pady=5)
    btn9 = Button(frame,text='9', padx=15, pady=10, command=lambda: button_clicked(9))
    btn9.grid(column=2, row=0, padx=5, pady=5)
    btn4 = Button(frame,text='4', padx=15, pady=10, command=lambda: button_clicked(4))
    btn4.grid(column=0, row=1, padx=5, pady=5)
    btn5 = Button(frame,text='5', padx=15, pady=10, command=lambda: button_clicked(5))
    btn5.grid(column=1, row=1, padx=5, pady=5)
    btn6 = Button(frame,text='6', padx=15, pady=10, command=lambda: button_clicked(6))
    btn6.grid(column=2, row=1, padx=5, pady=5)
    btn1 = Button(frame,text='1', padx=15, pady=10, command=lambda: button_clicked(1))
    btn1.grid(column=0, row=2, padx=5, pady=5)
    btn2 = Button(frame,text='2', padx=15, pady=10, command=lambda: button_clicked(2))
    btn2.grid(column=1, row=2, padx=5, pady=5)
    btn3 = Button(frame,text='3', padx=15, pady=10, command=lambda: button_clicked(3))
    btn3.grid(column=2, row=2, padx=5, pady=5)
    btn_pm = Button(frame,text='예약', padx=7, pady=10, command=lambda: button_clicked_str())
    btn_pm.grid(column=0, row=3, padx=5, pady=5)
    btn0 = Button(frame,text='0', padx=15, pady=10, command=lambda: button_clicked(0))
    btn0.grid(column=1, row=3, padx=5, pady=5)
    btn_p = Button(frame,text='<-', padx=12, pady=10, command=lambda: button_clear())
    btn_p.grid(column=2, row=3, padx=5, pady=5)

# 예약 버스 선택 함수
def qr_BusCheck(num):
    def qr_BusCheck_get():
        def qr_BusCheck_get_error():
            window4.destroy()
            qr_BusCheck(phonenum)

        def qr_BusCheck_get_back():
            window5.destroy()
            qr_BusCheck_cancel()

        def qr_BusCheck_get_reservation():
            window4.destroy()
            window5.destroy()
            msgbox1 = messagebox.askokcancel("확인 / 취소", qr_keyword + "번 버스를 예약하시겠습니까?")
            if (msgbox1 == 1):
                SeatCnt(qr_keyword, qr_remainSeatCnt1)
                Firebase_DB(phonenum, qr_keyword, qr_predictTime1, qr_locationNo1, qr_remainSeatCnt1, qr_plateNo1, startpoint, endpoint, qr_routeId, qr_stationSeq)
                msgbox1 = messagebox.showinfo('예약완료','정상적으로 예약 완료되었습니다')

        # 버스 API 추출
        qr_keyword = StringVar()
        qr_keyword = txt.get()
        flag1 = 0
        flag2 = 0
        qr_routeId = StringVar()
        qr_stationSeq = StringVar()

        serviceKey1='HQ7hhajrugx1f30ZP1IGJRkrv%2BLP7qKZVr9I1H%2FmweDkbNracDylSVzVGgOGmKccDF2g%2F%2BivtsCLldfp3QBg%2FQ%3D%3D'
        url1="http://apis.data.go.kr/6410000/busrouteservice/getAreaBusRouteList?serviceKey={}&areaId=13&keyword={}".format(serviceKey1,qr_keyword)
        #지역 수원 13 고정
    
        content = requests.get(url1).content # GET요청
        dict=xmltodict.parse(content) # XML을 dictionary로 파싱
        
        # 도착예정버스가 없을때를 검사하기
        jsonString = json.dumps(dict['response']['msgHeader'], ensure_ascii=False)
        jsonObj = json.loads(jsonString) # json을 dict으로 변환
        if(jsonObj['resultCode'] != '0'):
            msgbox = messagebox.showerror('에러','잘못된 버스 번호를 입력하였습니다')
            qr_BusCheck_get_error()

        jsonString = json.dumps(dict['response']['msgBody']['busRouteList'], ensure_ascii=False) # dict을 json으로 변환
        jsonObj = json.loads(jsonString) # json을 dict으로 변환
        if(len(jsonObj) != 6):
            for i in range(len(jsonObj)):
                if (jsonObj[i]['routeName'] == qr_keyword):
                    qr_routeId = jsonObj[i]['routeId']
                    flag1=1
            if(flag1 == 0):
                msgbox = messagebox.showerror('에러','현재 지역에서 운행하지 않는 버스 번호 입니다')
                qr_BusCheck_get_error()
        else:
            qr_routeId = jsonObj['routeId']      

        url2="http://apis.data.go.kr/6410000/busrouteservice/getBusRouteStationList?serviceKey={}&routeId={}".format(serviceKey1,qr_routeId)
    
        content = requests.get(url2).content # GET요청
        dict=xmltodict.parse(content) # XML을 dictionary로 파싱
        
        jsonString = json.dumps(dict['response']['msgBody']['busRouteStationList'], ensure_ascii=False) # dict을 json으로 변환
        jsonObj = json.loads(jsonString) # json을 dict으로 변환

        for i in range(len(jsonObj)):
            if (jsonObj[i]['stationId'] == qr_stationId):
                qr_stationSeq = jsonObj[i]['stationSeq'] #노선의 정류소 순번
                flag2 = 1
        if(flag2 == 0):
            msgbox = messagebox.showerror('에러','현재 정류장에 정차하지 않는 버스입니다')
            qr_BusCheck_get_error()

        serviceKey2='HQ7hhajrugx1f30ZP1IGJRkrv%2BLP7qKZVr9I1H%2FmweDkbNracDylSVzVGgOGmKccDF2g%2F%2BivtsCLldfp3QBg%2FQ%3D%3D'
        url3="http://apis.data.go.kr/6410000/busarrivalservice/getBusArrivalItem?serviceKey={}&stationId={}&routeId={}&staOrder={}".format(serviceKey2,qr_stationId,qr_routeId,qr_stationSeq)
    
        content = requests.get(url3).content # GET요청
        dict=xmltodict.parse(content) # XML을 dictionary로 파싱
        

        # 도착예정버스가 없을때를 검사하기
        jsonString = json.dumps(dict['response']['msgHeader'], ensure_ascii=False)
        jsonObj = json.loads(jsonString) # json을 dict으로 변환
        if(jsonObj['resultCode'] != '0'):
            msgbox = messagebox.showerror('에러','운행 중인 버스가 없습니다')
            qr_BusCheck_get_error()

        jsonString = json.dumps(dict['response']['msgBody']['busArrivalItem'], ensure_ascii=False) # dict을 json으로 변환
        jsonObj = json.loads(jsonString) # json을 dict으로 변환

        qr_predictTime1 = StringVar()
        qr_locationNo1 = StringVar()
        qr_remainSeatCnt1 = StringVar()
        qr_plateNo1 = StringVar()
        qr_predictTime2 = StringVar()
        qr_locationNo2 = StringVar()
        qr_remainSeatCnt2 = StringVar()
        qr_plateNo2 = StringVar()

        qr_predictTime1 = jsonObj['predictTime1']
        qr_locationNo1 = jsonObj['locationNo1']
        qr_remainSeatCnt1 = jsonObj['remainSeatCnt1']
        qr_plateNo1 = jsonObj['plateNo1']
        qr_predictTime2 = jsonObj['predictTime2']
        qr_locationNo2 = jsonObj['locationNo2']
        qr_remainSeatCnt2 = jsonObj['remainSeatCnt2']
        qr_plateNo2 = jsonObj['plateNo2']

        url4="http://apis.data.go.kr/6410000/busrouteservice/getBusRouteInfoItem?serviceKey={}&routeId={}".format(serviceKey2,qr_routeId)

        content = requests.get(url4).content # GET요청
        dict=xmltodict.parse(content) # XML을 dictionary로 파싱
        
        jsonString = json.dumps(dict['response']['msgBody']['busRouteInfoItem'], ensure_ascii=False) # dict을 json으로 변환
        jsonObj = json.loads(jsonString) # json을 dict으로 변환

        startpoint = StringVar()
        endpoint = StringVar()

        startpoint = jsonObj['startStationName']
        endpoint = jsonObj['endStationName']

        # Main - qr_BusCheck_get
        window5 = Tk()
        window5.title("버스 확인")
        window5.geometry("800x480")
        center(window5)

        frame1 = Frame(window5)
        frame1.pack(side=TOP, expand=YES)
        frame2 = Frame(window5)
        frame2.pack(side=TOP, expand=YES)

        textlabel0 = Label(frame1, text = qr_keyword + "번 버스")
        textlabel1 = Label(frame1, text = qr_predictTime1 + "분")
        textlabel2 = Label(frame1, text = qr_locationNo1 +"정류장")
        textlabel0.pack()
        textlabel1.pack()
        textlabel2.pack()
        if(qr_remainSeatCnt1 == "-1"):
            textlabel3 = Label(frame1, text = "남은 좌석이 존재하지 않습니다")
            textlabel3.pack()
        else:
            textlabel3 = Label(frame1, text = "남은 좌석 : " + qr_remainSeatCnt1)
            textlabel3.pack()
        if(qr_predictTime2 == None):
            textlabel4 = Label(frame1, text = "다음 버스가 존재하지 않습니다")
            textlabel4.pack()
        else:
            textlabel4 = Label(frame1, text = qr_predictTime2 + "분")
            textlabel5 = Label(frame1, text = qr_locationNo2 +"정류장")
            textlabel4.pack()
            textlabel5.pack()
            if(qr_remainSeatCnt1 == "-1"):
                textlabel6 = Label(frame1, text = "남은 좌석이 존재하지 않습니다")
                textlabel6.pack()
            else:
                textlabel6 = Label(frame1, text = "남은 좌석 : " + qr_remainSeatCnt2)
                textlabel6.pack()
                
        btn1 = Button(frame2, text = "back", command=qr_BusCheck_get_back).grid(row = 0, column = 0, padx = 10, pady = 10)
        btn2 = Button(frame2, text = "reservation", command=qr_BusCheck_get_reservation).grid(row = 0, column = 1, padx = 10, pady = 10)

        window5.mainloop()

    def qr_BusCheck_cancel():
        txt.delete(0, "end")

    def qr_BusCheck_back():
        window4.destroy()

    #Main
    window4 = Tk()
    window4.title("버스 예약")
    window4.geometry("800x480")
    center(window4)
    phonenum = num

    frame1 = Frame(window4)
    frame1.pack(side="left", expand=YES)
    frame2 = Frame(window4)
    frame2.pack(side="right", expand=YES)

    # frame1
    frame3 = Frame(frame1)
    frame3.pack(side="top", expand=YES)
    frame4 = Frame(frame1)
    frame4.pack(side="bottom", expand=YES)

    label = Label(frame3, text = "버스 번호를 입력하세요")
    label.pack(side = "top")
    txt = Entry(frame3, width=30)
    txt.pack(side = "bottom")
    txt.insert(0,"")

    btn1 = Button(frame4, text = "CHECK", command=qr_BusCheck_get).grid(row = 0, column = 0, padx = 10, pady = 50)
    btn2 = Button(frame4, text = "CANCEL", command=qr_BusCheck_cancel).grid(row = 0, column = 1, padx = 10, pady = 50)
    btn3 = Button(frame4, text = "BACK", command=qr_BusCheck_back).grid(row = 0, column = 2, padx = 10, pady = 50)

    # frame2
    KeyBoard(frame2, txt)

    window4.mainloop()

# 버스 확인 함수
def BusCheck():
    def BusCheck_get():

        def BusCheck_get_error():
            window2.destroy()
            BusCheck()

        def BusCheck_get_back():
            window3.destroy()
            BusCheck_cancel()

        # 버스 API 추출
        keyword = StringVar()
        keyword = txt.get()
        flag1 = 0 # 현재 지역에서 운행하는 버스인지 확인
        flag2 = 0 # 현재 정류장에 정차하는 버스인지 확인

        serviceKey1='HQ7hhajrugx1f30ZP1IGJRkrv%2BLP7qKZVr9I1H%2FmweDkbNracDylSVzVGgOGmKccDF2g%2F%2BivtsCLldfp3QBg%2FQ%3D%3D'
        url1="http://apis.data.go.kr/6410000/busrouteservice/getAreaBusRouteList?serviceKey={}&areaId=13&keyword={}".format(serviceKey1,keyword)
        #지역 수원 13 고정
    
        content = requests.get(url1).content # GET요청
        dict=xmltodict.parse(content) # XML을 dictionary로 파싱
        
        # 도착 예정 버스가 없을 때를 검사하기
        jsonString = json.dumps(dict['response']['msgHeader'], ensure_ascii=False)
        jsonObj = json.loads(jsonString) # json을 dict으로 변환
        if(jsonObj['resultCode'] != '0'):
            msgbox = messagebox.showerror('에러','잘못된 버스 번호를 입력하였습니다')
            BusCheck_get_error()

        jsonString = json.dumps(dict['response']['msgBody']['busRouteList'], ensure_ascii=False) # dict을 json으로 변환
        jsonObj = json.loads(jsonString) # json을 dict으로 변환
        if(len(jsonObj) != 6):
            for i in range(len(jsonObj)):
                if (jsonObj[i]['routeName'] == keyword):
                    routeId = jsonObj[i]['routeId']
                    flag1=1
            if(flag1 == 0):
                msgbox = messagebox.showerror('에러','현재 지역에서 운행하지 않는 버스 번호 입니다')
                BusCheck_get_error()
        else:
            routeId = jsonObj['routeId']

        url2="http://apis.data.go.kr/6410000/busrouteservice/getBusRouteStationList?serviceKey={}&routeId={}".format(serviceKey1,routeId)
    
        content = requests.get(url2).content # GET요청
        dict=xmltodict.parse(content) # XML을 dictionary로 파싱
        
        jsonString = json.dumps(dict['response']['msgBody']['busRouteStationList'], ensure_ascii=False) # dict을 json으로 변환
        jsonObj = json.loads(jsonString) # json을 dict으로 변환
    
        for i in range(len(jsonObj)):
            if (jsonObj[i]['stationId'] == stationId):
                stationSeq = jsonObj[i]['stationSeq'] #노선의 정류소 순번
                flag2 = 1
        if(flag2 == 0):
            msgbox = messagebox.showerror('에러','현재 정류장에 정차하지 않는 버스입니다')
            BusCheck_get_error()
            
        serviceKey2='HQ7hhajrugx1f30ZP1IGJRkrv%2BLP7qKZVr9I1H%2FmweDkbNracDylSVzVGgOGmKccDF2g%2F%2BivtsCLldfp3QBg%2FQ%3D%3D'
        url3="http://apis.data.go.kr/6410000/busarrivalservice/getBusArrivalItem?serviceKey={}&stationId={}&routeId={}&staOrder={}".format(serviceKey2,stationId,routeId,stationSeq)
    
        content = requests.get(url3).content # GET요청
        dict=xmltodict.parse(content) # XML을 dictionary로 파싱
        
        # 도착예정버스가 없을때를 검사하기
        jsonString = json.dumps(dict['response']['msgHeader'], ensure_ascii=False)
        jsonObj = json.loads(jsonString) # json을 dict으로 변환
        if(jsonObj['resultCode'] != '0'):
            msgbox = messagebox.showerror('에러','운행 중인 버스가 없습니다')
            BusCheck_get_error()

        jsonString = json.dumps(dict['response']['msgBody']['busArrivalItem'], ensure_ascii=False) # dict을 json으로 변환
        jsonObj = json.loads(jsonString) # json을 dict으로 변환

        predictTime1 = StringVar()
        locationNo1 = StringVar()
        remainSeatCnt1 = StringVar()
        predictTime2 = StringVar()
        locationNo2 = StringVar()
        remainSeatCnt2 = StringVar()

        predictTime1 = jsonObj['predictTime1']
        locationNo1 = jsonObj['locationNo1']
        remainSeatCnt1 = jsonObj['remainSeatCnt1']
        predictTime2 = jsonObj['predictTime2']
        locationNo2 = jsonObj['locationNo2']
        remainSeatCnt2 = jsonObj['remainSeatCnt2']

        # Main - BusCheck_get
        window3 = Tk()
        window3.title("버스 확인")
        window3.geometry("800x480")
        center(window3)

        frame1 = Frame(window3)
        frame1.pack(side=TOP, expand=YES)
        frame2 = Frame(window3)
        frame2.pack(side=TOP, expand=YES)

        textlabel0 = Label(frame1, text = keyword + "번 버스")
        textlabel1 = Label(frame1, text = predictTime1 + "분")
        textlabel2 = Label(frame1, text = locationNo1 +"정류장")
        textlabel0.pack()
        textlabel1.pack()
        textlabel2.pack()
        if(remainSeatCnt1 == "-1"):
            textlabel3 = Label(frame1, text = "남은 좌석이 존재하지 않습니다")
        else:
            textlabel3 = Label(frame1, text = "남은 좌석 : " + remainSeatCnt1)
        textlabel3.pack()
        if(predictTime2 == None):
            textlabel4 = Label(frame1, text = "다음 버스가 존재하지 않습니다")
            textlabel4.pack()
        else:
            textlabel4 = Label(frame1, text = predictTime2 + "분")
            textlabel5 = Label(frame1, text = locationNo2 +"정류장")
            textlabel4.pack()
            textlabel5.pack()
            if(remainSeatCnt1 == "-1"):
                textlabel6 = Label(frame1, text = "남은 좌석이 존재하지 않습니다")
            else:
                textlabel6 = Label(frame1, text = "남은 좌석 : " + remainSeatCnt2)
            textlabel6.pack()

        btn = Button(frame2, text = "back", command=BusCheck_get_back)
        btn.pack()

        window3.mainloop()

    def BusCheck_cancel():
        txt.delete(0, "end")

    def BusCheck_back():
        window2.destroy()

    #Main
    window2 = Tk()
    window2.title("대기 현황 조회")
    window2.geometry("800x480")
    center(window2)

    frame1 = Frame(window2)
    frame1.pack(side="left", expand=YES)
    frame2 = Frame(window2)
    frame2.pack(side="right", expand=YES)

    # frame1
    frame3 = Frame(frame1)
    frame3.pack(side="top", expand=YES)
    frame4 = Frame(frame1)
    frame4.pack(side="bottom", expand=YES)

    label = Label(frame3, text = "버스 번호를 입력하세요")
    label.pack(side = "top")
    txt = Entry(frame3, width=30)
    txt.pack(side = "bottom")
    txt.insert(0,"")

    btn1 = Button(frame4, text = "CHECK", command=BusCheck_get).grid(row = 0, column = 0, padx = 10, pady = 50)
    btn2 = Button(frame4, text = "CANCEL", command=BusCheck_cancel).grid(row = 0, column = 1, padx = 10, pady = 50)
    btn3 = Button(frame4, text = "BACK", command=BusCheck_back).grid(row = 0, column = 2, padx = 10, pady = 50)

    # frame2
    KeyBoard(frame2, txt)

    window2.mainloop()

# 키오스크 Main
def KioskMain():
    window = Tk()
    window.title("광역 버스 예약 시스템")
    window.geometry("800x480")
    center(window)

    frame1 = Frame(window)
    frame1.pack()

    Button(frame1, text="QR code", command=QrCode, width=10, height=2).grid(row = 0, column = 0, padx = 100, pady = 200)
    Button(frame1, text="Bus check", command=BusCheck, width=10, height=2).grid(row = 0, column = 1, padx = 100, pady = 200)
    
    window.mainloop()

# Main
if __name__=="__main__":

    p1 = threading.Thread(target=KioskMain) 
    p2 = threading.Thread(target=Firebase_update)

    p1.start()
    p2.start()

    p1.join()
    p2.join()