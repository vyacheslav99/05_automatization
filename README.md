# 05 automatization
Асинхронный http-сервер

## Описание ПО
Асинхронный http-сервер реализованный на чистых сокетах, без применения библиотек для работы с http и фреймворков.
При разработке сервера реализована архитектура thread pool.

### Особенности архитектуры
При старте сервер сразу создает пул подготовленных к работе потоков-обработчиков (thread, workers).
Количество обработчиков в пуле задается параметром в конфиге INIT_HANDLERS или параметром командной строки -w.
Данное кол-во потоков все время содержится в пуле готовыми к работе.
Если при поступлении нового соединения все обработчики в пуле заняты обработкой соединения, создается новый обработчик и добавляется в пул.
Т.о. пул расширяется по ходу работы сервера. Если начальный размер пула задан числом меньше 1, то пул создается пустой, но при
поступлении соединений так же в него добавляются новые обработчики. Пул может быть расширен до размера, указанного параметром MAX_HANDLERS.
При поступлении новых соединений, когда все потоки в пуле заняты и его размер равен максимальному, реализовано 2 варианта поведения (
определяются настройкой WHEN_REACHED_LIMIT): 0 - новые соединения будут сбрасываться сервером, пока не освободится какой-нибудь обработчик
или не уменьшиться размер пула; 1 - новое соединение будет добавляться в очередь случайному обработчику, он его соответсвенно обработает,
как только дойдет очередь.
Предусмотрен механизм очистки пула. При очистке из пула будут удаляться все свободные обработчики, пока его размер не станет равен начальному
(задаваемому параметром INIT_HANDLERS). Настройки стратегии очистки доступны в конфиге.

## Результаты тестирования
Все тесты, кроме одного проходят успешно.
В связи с особенностью реализации не проходит тест "directory index file absent".
Дело в том, что я немного отступил от Т.З. (точнее понял по своему, т.к. этот момент в Т.З. никак не регламентируется) и реализовал такую логику -
если запрос на папку, а не на файл, то по условиям задачи надо вернуть index.html из этой папки. Эта часть так и работает, но если в папке нет такого
файла, я сделал генерацию стандартного файла index.html, содержащего список папок/файлов указанной папки. Изначально сделано это было для удобства
отладки сервера на время разработки, но потом решил оставить это поведение.

## Результаты нагрузочного тестирования
E:\work\src\otus\05_automatization>e:\programs\apache2\bin\ab.exe -n 50000 -c 100 -r http://localhost:8080/dir2
This is ApacheBench, Version 2.3 <$Revision: 655654 $>
Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
Licensed to The Apache Software Foundation, http://www.apache.org/

Benchmarking localhost (be patient)
Completed 5000 requests
Completed 10000 requests
Completed 15000 requests
Completed 20000 requests
Completed 25000 requests
Completed 30000 requests
Completed 35000 requests
Completed 40000 requests
Completed 45000 requests
Completed 50000 requests
Finished 50000 requests


Server Software:        MyServer/1.0.0
Server Hostname:        localhost
Server Port:            8080

Document Path:          /dir2
Document Length:        34 bytes

Concurrency Level:      100
Time taken for tests:   133.883 seconds
Complete requests:      50000
Failed requests:        0
Write errors:           0
Total transferred:      8600000 bytes
HTML transferred:       1700000 bytes
Requests per second:    373.46 [#/sec] (mean)
Time per request:       267.767 [ms] (mean)
Time per request:       2.678 [ms] (mean, across all concurrent requests)
Transfer rate:          62.73 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    1  10.9      0     516
Processing:     0  267 111.4    250    1234
Waiting:        0  262 103.3    250     938
Total:          0  267 111.7    266    1234

Percentage of the requests served within a certain time (ms)
  50%    266
  66%    297
  75%    313
  80%    313
  90%    344
  95%    406
  98%    641
  99%    719
 100%   1234 (longest request)
