import requests
from bs4 import BeautifulSoup
import re
from time import sleep
from random import uniform,choice
from doubanUtils import *

headers0 = {'User-Agent':getAgent()}

subject_url_head = 'https://movie.douban.com/subject/'
movie_ppl_head = 'https://movie.douban.com/people/'

class Douban_Movie:
    def __init__(self,doubanid):
        self.s=requests.Session()
        #加上头部
        self.s.headers.update(headers0)
        self.id=doubanid
        #wish dict format: {movieid:[影片名,上映日期,导演,编剧,主演,制片国家/地区,片长,评分,评分人数,标记日期,豆瓣链接]}
        self.wish_dict={}
        self.Keys=['影片名','上映日期','导演','编剧',\
                    '主演','制片国家/地区','片长','评分','评分人数','豆瓣链接']
        #saw dict format: {movieid:[影片名,上映日期,导演,编剧,主演,制片国家/地区,片长,评分,评分人数,用户评分,评论,标记日期,豆瓣链接]}
        self.saw_dict={}
    
    def get_soup(self,url):
        req = self.s.get(url)
        return BeautifulSoup(req.text,'html.parser'), req.status_code

    def wish_get(self, wish):
        date=wish(class_=re.compile('date'))[0].get_text(strip=True)
        name=wish.find(href=re.compile('subject')).get_text(strip=True)
        mid=wish.find(href=re.compile('subject')).get('href').split('/')[-2]
        return date,name,mid

    def wish_store(self,wish):
        for i in range(len(wish)):
            date,name,mid = self.wish_get(wish[i])
            self.wish_dict[mid]=\
                {'影片名':name,'豆瓣链接':subject_url_head+mid,\
                '封面':' ','标记日期':date,'上映日期':' ','导演':' ','编剧':' ',\
                '主演':' ','制片国家/地区':' ','片长':' ','豆瓣评分':' ','评分人数':' '}

    def Wish(self):
        print('\n开始爬取'+self.id+'的想看列表')
        beg, end = pageControl(10)
        page=beg
        firstpage= movie_ppl_head +\
            self.id+'/wish?start='+str((beg-1)*30)+\
            '&sort=time&rating=all&filter=all&mode=list'
        soup,status=self.get_soup(firstpage)
        print(f'第{page}页',status)

        # get movie name and id
        self.wish_store(soup.find_all(class_=['item']))
        next_ = hasNextPage(soup)

        #get all wish list
        while (next_!=False) and (page < end):
            sleep(1.3)
            NextPage='https://movie.douban.com'+next_
            soup,status = self.get_soup(NextPage)
            page+=1
            print(f'第{page}页',status)
            self.wish_store(soup.find_all(class_=['item']))
            next_ = hasNextPage(soup)
        
        #add feature for every movie
        self.feature_helper(self.wish_dict)
        return self.wish_dict
    
    def feature_helper(self, dic):
        count=0
        st=perf_counter()
        total=len(dic)
        fail=[]
        for mid in dic.keys():
            count+=1
            if count%50==0:
                sleep(15)
            sleep(uniform(1.5,3))
            timebar(30,st,count/total)
            fail.append(self.get_feature(mid,dic))
        print('\n再次尝试打开失败的电影页')
        sleep(10)
        for fmid in fail:
            if fmid!=None:
                sleep(2)
                print()
                self.get_feature(fmid,dic)

    def get_feature(self,mid,dic):
        try:
            req2=self.s.get(subject_url_head+mid)
            print(' '+dic[mid]['影片名']+' 状态：',req2.status_code,end=' ')
            if req2.status_code == requests.codes.ok:
                soup2=BeautifulSoup(req2.text,'html.parser')
                c=soup2.find(id='info').text
                intro=c.split('\n')
                for i in intro:
                    if ':' in i :
                        key,value=i.split(':',1)
                        if key in self.Keys:
                            dic[mid][key]=value.strip(' ')
                dic[mid]['封面']=soup2.find('img').get('src')
                try:
                    dic[mid]['评分']=soup2.find(property=re.compile('average')).text
                except:
                    dic[mid]['评分']=''
                try:
                    dic[mid]['评分人数']=soup2.find(class_="rating_people").span.text
                except:
                    dic[mid]['评分人数']='0'
        except:
            print('\r打开电影页失败，失败的电影链接：'+subject_url_head+mid)
            self.switch_header()
            return mid
    
    def saw_get(self,saw):
        date=saw(class_=re.compile('date'))[0].get_text(strip=True)
        try:
            star=saw(class_=re.compile('rat'))[0]['class'][0][6]
        except:
            star=''
        try:
            comment=saw(class_=re.compile('comment'))[0].get_text(strip=True)
        except:
            comment=''
        try:
            owntag_list=saw.find(class_='tags').get_text(strip=True).split(': ',1)[1].split(' ')
            owntag='/'.join(owntag_list)
        except:
            owntag=''
        name=saw.find(href=re.compile('subject')).get_text(strip=True)
        mid=saw.find(href=re.compile('subject')).get('href').split('/')[-2]
        return date,star,comment,owntag,name,mid
    
    def saw_store(self,saw):
        for i in range(len(saw)):
            date,star,comment,owntag,name,mid=self.saw_get(saw[i])
            self.saw_dict[mid]=\
                {'影片名':name,'豆瓣链接':subject_url_head+mid,\
                '封面':'','用户评分':star,'短评':comment,\
                '用户标签':owntag,'标记日期':date,\
                '上映日期':'','导演':'','编剧':'',\
                '主演':'','制片国家/地区':'','片长':'','豆瓣评分':'',\
                '评分人数':''}

    def Saw(self):
        print('\n开始爬取'+self.id+'的看过列表')
        beg, end = pageControl(10)
        page=beg
        Sfirstpage = movie_ppl_head+self.id+'/collect?start='+\
            str((beg-1)*30)+'&sort=time&rating=all&filter=all&mode=list'
        soup,status = self.get_soup(Sfirstpage)
        print(f'第{page}页',status)

        #get movie name and id
        saw=soup.find_all(class_=['item'])
        self.saw_store(saw)
        next_ = hasNextPage(soup)
        #get all saw list
        while (next_ != False) and (page < end):
            sleep(1.3)
            NextPage='https://movie.douban.com' + next_
            soup,status = self.get_soup(NextPage)
            page+=1
            print(f'第{page}页',status)
            saw=soup.find_all(class_=['item'])
            self.saw_store(saw)
            next_ = hasNextPage(soup)
        
        #add feature for every movie
        self.feature_helper(self.saw_dict)
        return self.saw_dict
    
    def save_helper(self, dic, save_type):
        fw=open(fn(self.id+'-'+getFormatTime()+save_type+'plus.csv'),\
            'a',encoding='utf-8_sig')
        fw.write(','.join(list(dic[list(dic.keys())[0]].keys()))+'\n')
        for mid in dic.keys():
            fw.write(','.join(list(map(noco, dic[mid].values())))+'\n')
        fw.close()
    
    def save_as_csv(self,choice):
        if choice in ['a','c']:
            #保存想看
            self.save_helper(self.wish_dict,'想看')
        if choice in ['b','c']:
            #保存看过
            self.save_helper(self.saw_dict,'看过')
    
    def switch_header(self):
        headers0['User-Agent']=choice(user_agent_list)
        self.s.headers.update(headers0)

def main():
    print('嘿，据说你想要备份你的豆瓣电影记录？')
    print('''你需要知道：
    1. 本程序是一个爬虫程序，在爬取电影条目特征时会产生大量的网页访问，爬完后你的ip也许会被豆瓣封一段时间（登陆账号还是可以用啦）。
    2. 大量的网页访问意味着需要大量的流量。
    3. 爬取成功后，你的文件(csv)会被存储在该exe目录下，请不要在压缩包内使用该程序，解压后再使用。
    4. 可能会比较耗时。''')
    ans1=input('请确定你要开始备份(yes/no)： ')
    if ans1=='yes':
        Douid=input('请输入你的豆瓣id： ')
        clawer=Douban_Movie(doubanid=Douid)
        print('''
以下为选项
    A：想看列表
    B：看过列表
    C：想看+看过''')
        ans2=input('请输入你需要爬取的内容：')
        ans2=ans2.lower()
        if ans2=='a':
            clawer.Wish()
        elif ans2=='b':
            clawer.Saw()
        elif ans2=='c':
            clawer.Wish()
            clawer.Saw()
        clawer.save_as_csv(choice=ans2)
    print('\n问题反馈：jimsun6428@gmail.com | https://github.com/JimSunJing/douban_clawer')

if __name__ == '__main__':
    main()
    sleep(10)
    over=input('按任意键退出')