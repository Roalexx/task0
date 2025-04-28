Bu proje Flask ile  gelirstirileren bir RestAPI sayesinde kullanicidan gelen gorevleri bir Redis kuyruguna ekler ve bu gorevler arka planda RQ ile islenir.

Projenin temel hedefi uzun surebilecek tersine cevirme, buyuk harfe cevirme ve sayi toplama gibi islemleri APi dan ayirarak sistemin Asenkron calisabilmesini saglar.

KURULUM

    1. Projeyi Klonla
    ##bash
    git clone git@github.com:Roalexx/task0.git
    cd task0

    2. Docker Desktop Yukle
    https://www.docker.com/products/docker-desktop/

    3. Docker Desktop Calistir

    4. Docker'i Ayaga Kaldir
    ##bash
    docker compose up --build

    5. swagger Uzerinden Sistem Kullanilmaya Hazir
    http://localhost:5000/apidocs/

ORNEK API ISTEKLERI

    Gorev Olustur POST /task
        ##json 
        POST http://localhost:5000/tasks
        Content-Type: application/json

        {
            "task_type": "reverse_text",
            "data": "Merhaba"
        }

    Gorev Soucunu Al GET /resulsts/<task_id>
        ##http
        GET http://localhost:5000/results/<task_id>


    Bekleyen Gorevleri Goruntule GET /queue
        ##http
        GET http://localhost:5000/queue

    Tamamlanan Tum Gorevleri Goruntule GET /results
        ##http
        GET http://localhost:5000/results

KULLANIM SEKLI
    POST /task --> Gorev gonder
    GET /reuslts/<task_id> --> Sonuc al
    rq worker  --> Arka panda kuyrugu isler
    Tum gorevler task/py icinde tanimli fonksiyonlar uzerinden caisir

KULLANILAN KUTUPHANLER

-flask       -rest api 
-flasgger    -kullanici arayuzu
-celery      -que sistem duzenleyici
-redis       -que icin database 
-pika        -que'daki verilere erisebilmek 
