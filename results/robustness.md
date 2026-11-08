# Robustness checks

```
                                           annual                                             max_dd                                             ret_dd                                            
window                                      train   test   full 2007-2021 2007-2013 2014-2021  train   test   full 2007-2021 2007-2013 2014-2021  train   test   full 2007-2021 2007-2013 2014-2021
check       variant                                                                                                                                                                                
cost        core cost 0.05%                 0.137  0.253  0.179       NaN       NaN       NaN -0.284 -0.113 -0.284       NaN       NaN       NaN  0.483  2.248  0.632       NaN       NaN       NaN
            account cost 0.05% margin 6.5%  0.159  0.252  0.193       NaN       NaN       NaN -0.294 -0.127 -0.294       NaN       NaN       NaN  0.541  1.987  0.657       NaN       NaN       NaN
            account cost 0.05% margin 8.0%  0.157  0.250  0.191       NaN       NaN       NaN -0.294 -0.127 -0.294       NaN       NaN       NaN  0.535  1.971  0.651       NaN       NaN       NaN
            core cost 0.10%                 0.132  0.249  0.174       NaN       NaN       NaN -0.290 -0.113 -0.290       NaN       NaN       NaN  0.453  2.211  0.601       NaN       NaN       NaN
            account cost 0.10% margin 6.5%  0.151  0.244  0.185       NaN       NaN       NaN -0.301 -0.129 -0.301       NaN       NaN       NaN  0.502  1.885  0.615       NaN       NaN       NaN
            account cost 0.10% margin 8.0%  0.149  0.242  0.183       NaN       NaN       NaN -0.301 -0.129 -0.301       NaN       NaN       NaN  0.496  1.869  0.609       NaN       NaN       NaN
            core cost 0.20%                 0.121  0.241  0.165       NaN       NaN       NaN -0.303 -0.116 -0.303       NaN       NaN       NaN  0.399  2.084  0.544       NaN       NaN       NaN
            account cost 0.20% margin 6.5%  0.134  0.228  0.168       NaN       NaN       NaN -0.314 -0.135 -0.314       NaN       NaN       NaN  0.427  1.684  0.537       NaN       NaN       NaN
            account cost 0.20% margin 8.0%  0.132  0.226  0.167       NaN       NaN       NaN -0.314 -0.135 -0.314       NaN       NaN       NaN  0.422  1.669  0.531       NaN       NaN       NaN
old_period  QQQ>SMA200 else GLD               NaN    NaN    NaN     0.146     0.121     0.167    NaN    NaN    NaN    -0.295    -0.278    -0.295    NaN    NaN    NaN     0.494     0.437     0.567
            SPY>SMA200 else IEF               NaN    NaN    NaN     0.085     0.066     0.101    NaN    NaN    NaN    -0.266    -0.266    -0.222    NaN    NaN    NaN     0.317     0.246     0.457
            SPY>SMA200 else GLD               NaN    NaN    NaN     0.101     0.065     0.133    NaN    NaN    NaN    -0.371    -0.371    -0.297    NaN    NaN    NaN     0.272     0.175     0.449
            QQQ>SMA200 else IEF               NaN    NaN    NaN     0.119     0.094     0.141    NaN    NaN    NaN    -0.264    -0.252    -0.264    NaN    NaN    NaN     0.451     0.374     0.535
            QQQ buy&hold                      NaN    NaN    NaN     0.170     0.116     0.219    NaN    NaN    NaN    -0.534    -0.534    -0.286    NaN    NaN    NaN     0.318     0.217     0.766
            SPY buy&hold                      NaN    NaN    NaN     0.106     0.061     0.147    NaN    NaN    NaN    -0.552    -0.552    -0.337    NaN    NaN    NaN     0.192     0.110     0.435
delay       core +1 day delay               0.127  0.234  0.166       NaN       NaN       NaN -0.301 -0.113 -0.301       NaN       NaN       NaN  0.423  2.074  0.553       NaN       NaN       NaN
            core baseline                   0.137  0.253  0.179       NaN       NaN       NaN -0.284 -0.113 -0.284       NaN       NaN       NaN  0.483  2.248  0.632       NaN       NaN       NaN
sensitivity SMA100                          0.087  0.179  0.121       NaN       NaN       NaN -0.278 -0.195 -0.278       NaN       NaN       NaN  0.313  0.916  0.434       NaN       NaN       NaN
            SMA125                          0.133  0.143  0.137       NaN       NaN       NaN -0.272 -0.225 -0.272       NaN       NaN       NaN  0.490  0.638  0.504       NaN       NaN       NaN
            SMA150                          0.177  0.176  0.177       NaN       NaN       NaN -0.235 -0.198 -0.235       NaN       NaN       NaN  0.754  0.886  0.752       NaN       NaN       NaN
            SMA175                          0.177  0.230  0.196       NaN       NaN       NaN -0.221 -0.137 -0.221       NaN       NaN       NaN  0.799  1.672  0.888       NaN       NaN       NaN
            SMA200                          0.137  0.253  0.179       NaN       NaN       NaN -0.284 -0.113 -0.284       NaN       NaN       NaN  0.483  2.248  0.632       NaN       NaN       NaN
            SMA225                          0.104  0.216  0.145       NaN       NaN       NaN -0.312 -0.132 -0.312       NaN       NaN       NaN  0.335  1.640  0.466       NaN       NaN       NaN
            SMA250                          0.084  0.220  0.133       NaN       NaN       NaN -0.360 -0.153 -0.360       NaN       NaN       NaN  0.233  1.439  0.369       NaN       NaN       NaN
```

## Monte Carlo
Sleeve trade-order reshuffle: {'n_trades': 68, 'real_dd': np.float64(-0.031002527323016893), 'p5': np.float64(-0.033628407408689096), 'p50': np.float64(-0.02152185201350898)}

Block bootstrap (20d, 2000 paths): {'ann_p5': np.float64(0.07573944051381223), 'ann_p50': np.float64(0.228569708620469), 'ann_p95': np.float64(0.39479999225406864), 'dd_p5': np.float64(-0.34067783483748154), 'dd_p50': np.float64(-0.20821648277543792), 'dd_p95': np.float64(-0.1404123694088372), 'p_dd_worse_30': 0.107, 'p_ann_below_0': 0.007}
