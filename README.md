# pabotscope

Show pabot thread usage trends

## Usage

After you have run pabot, save it's output into a file. Pabotscope will read it and print a graph showing how many processes
are running in parallel. This can be identify if end of testrun has long tests that making test run longer than necessary.

```sh
pabot --processes 4  demo 2>&1 | tee pabot.log
<pabot output removed>

python src/pabotscope.py pabot.log

 ▓▓▓▓▓▓
 ▓▓▓▓▓▓
 ▓▓▓▓▓▓
 ▓▓▓▓▓▓▓
 ▓▓▓▓▓▓▓
 ▓▓▓▓▓▓▓
 ▓▓▓▓▓▓▓
 ▓▓▓▓▓▓▓
▓▓▓▓▓▓▓▓▓▓▓▓
▓▓▓▓▓▓▓▓▓▓▓▓

Top Longest Running Tests:
--------------------------------------------------
Test Name                           Duration (s)
--------------------------------------------------
Demo.Test4                                 10.30
Demo.Test2                                  6.40
Demo.Test3                                  4.40
Demo.Test1                                  3.40
Demo.Test0                                  1.40
Demo.Test5                                  1.30
Demo.Test6                                  1.30
Demo.Test7                                  1.30
Demo.Test8                                  1.30
Demo.Test9                                  1.30
--------------------------------------------------
```
