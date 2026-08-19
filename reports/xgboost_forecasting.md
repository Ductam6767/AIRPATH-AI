# AIRPATH-AI XGBoost forecasting foundation

## Protocol

This remains an **hourly monitored-station forecasting experiment**. Three
direct models are pooled across stations, one each for t+1h, t+2h, and t+3h.
Station identity is one-hot encoded and is not interpreted as ordinal.

V1 uses exact PM2.5(t-1h), PM2.5(t-2h), PM2.5(t-3h), origin hour, day of week,
month, and station. V2 adds temperature and humidity observed at prediction
time. Current PM2.5(t), future values, secondary pollutants, target-quality
flags, and test information are not model features.

| split      | start               | end                 |   unique_timestamps |
|:-----------|:--------------------|:--------------------|--------------------:|
| train      | 2021-02-23 21:00:00 | 2022-01-31 02:00:00 |                7316 |
| validation | 2022-01-31 03:00:00 | 2022-04-08 00:00:00 |                1568 |
| test       | 2022-04-08 01:00:00 | 2022-06-21 17:00:00 |                1568 |

Hyperparameters were selected independently by horizon using validation MAE
from four declared candidates. Test rows were not accepted by the selection
function. V2 used the selected V1 parameters unchanged as a controlled feature
ablation. Version selection used pooled validation MAE. The selected version was
**V1**. After freezing this decision, V1 and V2 were
refit on train+validation and each evaluated once on the locked test partition.

## Selected V1 hyperparameters

|   horizon_hours |   n_estimators |   max_depth |   learning_rate |   subsample |   colsample_bytree |   min_child_weight |
|----------------:|---------------:|------------:|----------------:|------------:|-------------------:|-------------------:|
|          1.0000 |       250.0000 |      3.0000 |          0.0500 |      0.9000 |             0.9000 |             1.0000 |
|          2.0000 |       250.0000 |      3.0000 |          0.0500 |      0.9000 |             0.9000 |             1.0000 |
|          3.0000 |       150.0000 |      3.0000 |          0.1000 |      1.0000 |             0.9000 |             1.0000 |

Complete search results are saved in
`reports/tables/xgboost_validation_search.csv`.

## A. V1 validation results

| model      | split      | Station_No   | horizon_hours   |     n |    mae |   rmse |     r2 |
|:-----------|:-----------|:-------------|:----------------|------:|-------:|-------:|-------:|
| xgboost_v1 | validation | ALL          | ALL             | 25744 | 5.5771 | 8.9357 | 0.4353 |
| xgboost_v1 | validation | ALL          | 1               |  8603 | 4.6986 | 8.0883 | 0.5384 |
| xgboost_v1 | validation | ALL          | 2               |  8580 | 5.6768 | 9.0076 | 0.4257 |
| xgboost_v1 | validation | ALL          | 3               |  8561 | 6.3599 | 9.6461 | 0.3408 |

## B. V1 final locked-test results

| model      | split   | Station_No   | horizon_hours   |     n |    mae |   rmse |     r2 |
|:-----------|:--------|:-------------|:----------------|------:|-------:|-------:|-------:|
| xgboost_v1 | test    | ALL          | ALL             | 23655 | 5.1726 | 8.2867 | 0.4769 |
| xgboost_v1 | test    | ALL          | 1               |  7929 | 4.4333 | 7.5261 | 0.5705 |
| xgboost_v1 | test    | ALL          | 2               |  7883 | 5.2738 | 8.3529 | 0.4679 |
| xgboost_v1 | test    | ALL          | 3               |  7843 | 5.8184 | 8.9287 | 0.3905 |

## C–D. Comparison with persistence and historical baseline

| model           | split      | Station_No   | horizon_hours   |     n |    mae |    rmse |      r2 |
|:----------------|:-----------|:-------------|:----------------|------:|-------:|--------:|--------:|
| persistence     | validation | ALL          | ALL             | 25744 | 4.4866 |  9.2182 |  0.3990 |
| persistence     | validation | ALL          | 1               |  8603 | 3.0381 |  7.0253 |  0.6518 |
| persistence     | validation | ALL          | 2               |  8580 | 4.6392 |  9.4533 |  0.3675 |
| persistence     | validation | ALL          | 3               |  8561 | 5.7893 | 10.7874 |  0.1756 |
| persistence     | test       | ALL          | ALL             | 23655 | 4.3162 |  8.7469 |  0.4172 |
| persistence     | test       | ALL          | 1               |  7929 | 2.9996 |  7.1405 |  0.6134 |
| persistence     | test       | ALL          | 2               |  7883 | 4.4941 |  8.8765 |  0.3991 |
| persistence     | test       | ALL          | 3               |  7843 | 5.4684 | 10.0006 |  0.2354 |
| historical_time | validation | ALL          | ALL             | 25744 | 8.2669 | 11.2472 |  0.1053 |
| historical_time | validation | ALL          | 1               |  8603 | 8.2712 | 11.2583 |  0.1058 |
| historical_time | validation | ALL          | 2               |  8580 | 8.2652 | 11.2433 |  0.1052 |
| historical_time | validation | ALL          | 3               |  8561 | 8.2642 | 11.2400 |  0.1050 |
| historical_time | test       | ALL          | ALL             | 23655 | 8.6403 | 11.4557 |  0.0003 |
| historical_time | test       | ALL          | 1               |  7929 | 8.6546 | 11.4607 |  0.0040 |
| historical_time | test       | ALL          | 2               |  7883 | 8.6361 | 11.4529 | -0.0004 |
| historical_time | test       | ALL          | 3               |  7843 | 8.6299 | 11.4534 | -0.0029 |
| xgboost_v1      | test       | ALL          | ALL             | 23655 | 5.1726 |  8.2867 |  0.4769 |
| xgboost_v1      | test       | ALL          | 1               |  7929 | 4.4333 |  7.5261 |  0.5705 |
| xgboost_v1      | test       | ALL          | 2               |  7883 | 5.2738 |  8.3529 |  0.4679 |
| xgboost_v1      | test       | ALL          | 3               |  7843 | 5.8184 |  8.9287 |  0.3905 |
| xgboost_v1      | validation | ALL          | ALL             | 25744 | 5.5771 |  8.9357 |  0.4353 |
| xgboost_v1      | validation | ALL          | 1               |  8603 | 4.6986 |  8.0883 |  0.5384 |
| xgboost_v1      | validation | ALL          | 2               |  8580 | 5.6768 |  9.0076 |  0.4257 |
| xgboost_v1      | validation | ALL          | 3               |  8561 | 6.3599 |  9.6461 |  0.3408 |
| xgboost_v2      | test       | ALL          | ALL             | 23655 | 5.2693 |  8.4237 |  0.4594 |
| xgboost_v2      | test       | ALL          | 1               |  7929 | 4.5206 |  7.6462 |  0.5567 |
| xgboost_v2      | test       | ALL          | 2               |  7883 | 5.3868 |  8.4747 |  0.4522 |
| xgboost_v2      | test       | ALL          | 3               |  7843 | 5.9081 |  9.0951 |  0.3676 |
| xgboost_v2      | validation | ALL          | ALL             | 25744 | 5.5951 |  9.0573 |  0.4198 |
| xgboost_v2      | validation | ALL          | 1               |  8603 | 4.6883 |  8.1662 |  0.5295 |
| xgboost_v2      | validation | ALL          | 2               |  8580 | 5.7165 |  9.0852 |  0.4158 |
| xgboost_v2      | validation | ALL          | 3               |  8561 | 6.3846 |  9.8463 |  0.3132 |

Positive MAE/RMSE improvement means lower error than persistence. R² is reported
as an absolute difference because percentage changes in R² are not meaningful
when baseline R² can be zero or negative.

| model      | split      | Station_No   | horizon_hours   |     n |    mae |   rmse |     r2 |   persistence_mae |   persistence_rmse |   persistence_r2 |   mae_absolute_improvement |   mae_percent_improvement |   rmse_absolute_improvement |   rmse_percent_improvement |   r2_absolute_improvement |
|:-----------|:-----------|:-------------|:----------------|------:|-------:|-------:|-------:|------------------:|-------------------:|-----------------:|---------------------------:|--------------------------:|----------------------------:|---------------------------:|--------------------------:|
| xgboost_v1 | test       | ALL          | ALL             | 23655 | 5.1726 | 8.2867 | 0.4769 |            4.3162 |             8.7469 |           0.4172 |                    -0.8565 |                  -19.8430 |                      0.4602 |                     5.2609 |                    0.0597 |
| xgboost_v1 | test       | ALL          | 1               |  7929 | 4.4333 | 7.5261 | 0.5705 |            2.9996 |             7.1405 |           0.6134 |                    -1.4338 |                  -47.7999 |                     -0.3856 |                    -5.4004 |                   -0.0429 |
| xgboost_v1 | test       | ALL          | 2               |  7883 | 5.2738 | 8.3529 | 0.4679 |            4.4941 |             8.8765 |           0.3991 |                    -0.7797 |                  -17.3497 |                      0.5236 |                     5.8992 |                    0.0688 |
| xgboost_v1 | test       | ALL          | 3               |  7843 | 5.8184 | 8.9287 | 0.3905 |            5.4684 |            10.0006 |           0.2354 |                    -0.3499 |                   -6.3993 |                      1.0719 |                    10.7184 |                    0.1551 |
| xgboost_v1 | validation | ALL          | ALL             | 25744 | 5.5771 | 8.9357 | 0.4353 |            4.4866 |             9.2182 |           0.3990 |                    -1.0905 |                  -24.3049 |                      0.2825 |                     3.0646 |                    0.0363 |
| xgboost_v1 | validation | ALL          | 1               |  8603 | 4.6986 | 8.0883 | 0.5384 |            3.0381 |             7.0253 |           0.6518 |                    -1.6605 |                  -54.6572 |                     -1.0630 |                   -15.1309 |                   -0.1133 |
| xgboost_v1 | validation | ALL          | 2               |  8580 | 5.6768 | 9.0076 | 0.4257 |            4.6392 |             9.4533 |           0.3675 |                    -1.0377 |                  -22.3671 |                      0.4457 |                     4.7144 |                    0.0582 |
| xgboost_v1 | validation | ALL          | 3               |  8561 | 6.3599 | 9.6461 | 0.3408 |            5.7893 |            10.7874 |           0.1756 |                    -0.5705 |                   -9.8551 |                      1.1413 |                    10.5798 |                    0.1652 |
| xgboost_v2 | test       | ALL          | ALL             | 23655 | 5.2693 | 8.4237 | 0.4594 |            4.3162 |             8.7469 |           0.4172 |                    -0.9531 |                  -22.0823 |                      0.3232 |                     3.6949 |                    0.0423 |
| xgboost_v2 | test       | ALL          | 1               |  7929 | 4.5206 | 7.6462 | 0.5567 |            2.9996 |             7.1405 |           0.6134 |                    -1.5211 |                  -50.7101 |                     -0.5057 |                    -7.0826 |                   -0.0567 |
| xgboost_v2 | test       | ALL          | 2               |  7883 | 5.3868 | 8.4747 | 0.4522 |            4.4941 |             8.8765 |           0.3991 |                    -0.8927 |                  -19.8630 |                      0.4018 |                     4.5264 |                    0.0532 |
| xgboost_v2 | test       | ALL          | 3               |  7843 | 5.9081 | 9.0951 | 0.3676 |            5.4684 |            10.0006 |           0.2354 |                    -0.4397 |                   -8.0403 |                      0.9054 |                     9.0540 |                    0.1322 |
| xgboost_v2 | validation | ALL          | ALL             | 25744 | 5.5951 | 9.0573 | 0.4198 |            4.4866 |             9.2182 |           0.3990 |                    -1.1084 |                  -24.7057 |                      0.1609 |                     1.7452 |                    0.0208 |
| xgboost_v2 | validation | ALL          | 1               |  8603 | 4.6883 | 8.1662 | 0.5295 |            3.0381 |             7.0253 |           0.6518 |                    -1.6502 |                  -54.3181 |                     -1.1409 |                   -16.2403 |                   -0.1223 |
| xgboost_v2 | validation | ALL          | 2               |  8580 | 5.7165 | 9.0852 | 0.4158 |            4.6392 |             9.4533 |           0.3675 |                    -1.0773 |                  -23.2210 |                      0.3681 |                     3.8943 |                    0.0483 |
| xgboost_v2 | validation | ALL          | 3               |  8561 | 6.3846 | 9.8463 | 0.3132 |            5.7893 |            10.7874 |           0.1756 |                    -0.5953 |                  -10.2820 |                      0.9411 |                     8.7242 |                    0.1376 |

### Scientific interpretation of baseline comparison

The selected V1 configuration does **not** uniformly outperform persistence.
On the locked test set its pooled MAE is higher by 0.8565 (19.84% worse), while
its pooled RMSE is lower by 0.4602 (5.26% better) and R² is higher by 0.0597.
Persistence is stronger at t+1h on all three metrics. At t+2h and t+3h, V1 has
lower RMSE and higher R² but still higher MAE. Thus the evidence depends on the
error functional; AIRPATH should not claim that V1 supersedes persistence.

V1 is materially better than the historical-time baseline on the locked test
set. However, V1 deliberately follows the requested feature contract and omits
PM2.5(t), whereas persistence uses PM2.5(t). The recency mismatch is an important
methodological limitation and plausibly contributes to persistence's MAE
advantage. It was not changed after observing test results.

## E. Locked-test station-level results

| model           | split   |   Station_No | horizon_hours   |    n |     mae |    rmse |      r2 |
|:----------------|:--------|-------------:|:----------------|-----:|--------:|--------:|--------:|
| persistence     | test    |            1 | ALL             | 4600 |  4.6658 |  7.8477 |  0.5861 |
| persistence     | test    |            2 | ALL             | 4206 |  3.6330 |  5.8158 |  0.3888 |
| persistence     | test    |            3 | ALL             | 2896 |  4.9509 |  7.5621 |  0.2153 |
| persistence     | test    |            4 | ALL             | 4174 |  5.9723 |  9.5603 |  0.4493 |
| persistence     | test    |            5 | ALL             | 3492 |  2.3902 |  3.9996 |  0.8333 |
| persistence     | test    |            6 | ALL             | 4287 |  4.1389 | 13.4996 | -0.3765 |
| historical_time | test    |            1 | ALL             | 4600 | 10.4665 | 13.0092 | -0.1373 |
| historical_time | test    |            2 | ALL             | 4206 |  6.2077 |  7.7777 | -0.0931 |
| historical_time | test    |            3 | ALL             | 2896 | 11.0521 | 12.6595 | -1.1990 |
| historical_time | test    |            4 | ALL             | 4174 |  9.3551 | 12.3884 |  0.0753 |
| historical_time | test    |            5 | ALL             | 3492 |  8.4289 | 10.4307 | -0.1341 |
| historical_time | test    |            6 | ALL             | 4287 |  6.9142 | 11.6989 | -0.0338 |
| xgboost_v1      | test    |            1 | ALL             | 4600 |  6.0325 |  8.5202 |  0.5122 |
| xgboost_v1      | test    |            2 | ALL             | 4206 |  3.9912 |  5.9136 |  0.3681 |
| xgboost_v1      | test    |            3 | ALL             | 2896 |  5.8652 |  7.7214 |  0.1819 |
| xgboost_v1      | test    |            4 | ALL             | 4174 |  6.4480 |  9.5849 |  0.4464 |
| xgboost_v1      | test    |            5 | ALL             | 3492 |  4.4534 |  5.8804 |  0.6396 |
| xgboost_v1      | test    |            6 | ALL             | 4287 |  4.2854 | 10.4313 |  0.1781 |
| xgboost_v2      | test    |            1 | ALL             | 4600 |  6.3194 |  9.0092 |  0.4545 |
| xgboost_v2      | test    |            2 | ALL             | 4206 |  3.9961 |  5.9547 |  0.3593 |
| xgboost_v2      | test    |            3 | ALL             | 2896 |  5.7730 |  7.6699 |  0.1928 |
| xgboost_v2      | test    |            4 | ALL             | 4174 |  6.5934 |  9.6472 |  0.4392 |
| xgboost_v2      | test    |            5 | ALL             | 3492 |  4.5855 |  6.0168 |  0.6226 |
| xgboost_v2      | test    |            6 | ALL             | 4287 |  4.3191 | 10.4791 |  0.1705 |

## F. Locked-test station-by-horizon results

| model           | split   |   Station_No |   horizon_hours |    n |     mae |    rmse |      r2 |
|:----------------|:--------|-------------:|----------------:|-----:|--------:|--------:|--------:|
| persistence     | test    |            1 |               1 | 1540 |  3.1516 |  5.3767 |  0.8055 |
| persistence     | test    |            1 |               2 | 1533 |  4.8169 |  7.9984 |  0.5704 |
| persistence     | test    |            1 |               3 | 1527 |  6.0412 |  9.5992 |  0.3810 |
| persistence     | test    |            2 |               1 | 1407 |  2.5085 |  3.9772 |  0.7156 |
| persistence     | test    |            2 |               2 | 1402 |  3.7939 |  5.9032 |  0.3707 |
| persistence     | test    |            2 |               3 | 1397 |  4.6042 |  7.1364 |  0.0743 |
| persistence     | test    |            3 |               1 |  974 |  3.5683 |  5.5566 |  0.5828 |
| persistence     | test    |            3 |               2 |  965 |  5.1640 |  7.7451 |  0.1728 |
| persistence     | test    |            3 |               3 |  957 |  6.1433 |  9.0077 | -0.1256 |
| persistence     | test    |            4 |               1 | 1404 |  4.1900 |  6.7799 |  0.7255 |
| persistence     | test    |            4 |               2 | 1390 |  6.2348 |  9.7999 |  0.4199 |
| persistence     | test    |            4 |               3 | 1380 |  7.5210 | 11.5304 |  0.1935 |
| persistence     | test    |            5 |               1 | 1169 |  1.4984 |  2.4872 |  0.9354 |
| persistence     | test    |            5 |               2 | 1164 |  2.4985 |  4.0444 |  0.8295 |
| persistence     | test    |            5 |               3 | 1159 |  3.1809 |  5.0527 |  0.7342 |
| persistence     | test    |            6 |               1 | 1435 |  2.9900 | 12.8148 | -0.2446 |
| persistence     | test    |            6 |               2 | 1429 |  4.3147 | 13.5862 | -0.3943 |
| persistence     | test    |            6 |               3 | 1423 |  5.1209 | 14.0732 | -0.4908 |
| historical_time | test    |            1 |               1 | 1540 | 10.4641 | 13.0016 | -0.1371 |
| historical_time | test    |            1 |               2 | 1533 | 10.4702 | 13.0119 | -0.1370 |
| historical_time | test    |            1 |               3 | 1527 | 10.4651 | 13.0142 | -0.1378 |
| historical_time | test    |            2 |               1 | 1407 |  6.2257 |  7.7992 | -0.0936 |
| historical_time | test    |            2 |               2 | 1402 |  6.2087 |  7.7801 | -0.0931 |
| historical_time | test    |            2 |               3 | 1397 |  6.1886 |  7.7535 | -0.0927 |
| historical_time | test    |            3 |               1 |  974 | 11.0131 | 12.6105 | -1.1488 |
| historical_time | test    |            3 |               2 |  965 | 11.0423 | 12.6542 | -1.2082 |
| historical_time | test    |            3 |               3 |  957 | 11.1018 | 12.7146 | -1.2426 |
| historical_time | test    |            4 |               1 | 1404 |  9.4346 | 12.4516 |  0.0741 |
| historical_time | test    |            4 |               2 | 1390 |  9.3375 | 12.3754 |  0.0749 |
| historical_time | test    |            4 |               3 | 1380 |  9.2920 | 12.3370 |  0.0768 |
| historical_time | test    |            5 |               1 | 1169 |  8.4266 | 10.4244 | -0.1342 |
| historical_time | test    |            5 |               2 | 1164 |  8.4268 | 10.4295 | -0.1336 |
| historical_time | test    |            5 |               3 | 1159 |  8.4333 | 10.4383 | -0.1345 |
| historical_time | test    |            6 |               1 | 1435 |  6.9160 | 11.6856 | -0.0349 |
| historical_time | test    |            6 |               2 | 1429 |  6.9133 | 11.6986 | -0.0338 |
| historical_time | test    |            6 |               3 | 1423 |  6.9131 | 11.7127 | -0.0327 |
| xgboost_v1      | test    |            1 |               1 | 1540 |  5.0418 |  7.3521 |  0.6364 |
| xgboost_v1      | test    |            1 |               2 | 1533 |  6.1431 |  8.5870 |  0.5048 |
| xgboost_v1      | test    |            1 |               3 | 1527 |  6.9206 |  9.4945 |  0.3944 |
| xgboost_v1      | test    |            2 |               1 | 1407 |  3.4686 |  5.2546 |  0.5036 |
| xgboost_v1      | test    |            2 |               2 | 1402 |  4.0522 |  5.9861 |  0.3529 |
| xgboost_v1      | test    |            2 |               3 | 1397 |  4.4564 |  6.4433 |  0.2454 |
| xgboost_v1      | test    |            3 |               1 |  974 |  5.1575 |  7.0323 |  0.3318 |
| xgboost_v1      | test    |            3 |               2 |  965 |  6.0014 |  7.8419 |  0.1520 |
| xgboost_v1      | test    |            3 |               3 |  957 |  6.4480 |  8.2508 |  0.0556 |
| xgboost_v1      | test    |            4 |               1 | 1404 |  5.6946 |  8.6641 |  0.5517 |
| xgboost_v1      | test    |            4 |               2 | 1390 |  6.5689 |  9.7105 |  0.4304 |
| xgboost_v1      | test    |            4 |               3 | 1380 |  7.0928 | 10.3210 |  0.3539 |
| xgboost_v1      | test    |            5 |               1 | 1169 |  3.5628 |  4.7724 |  0.7623 |
| xgboost_v1      | test    |            5 |               2 | 1164 |  4.5625 |  5.9695 |  0.6286 |
| xgboost_v1      | test    |            5 |               3 | 1159 |  5.2423 |  6.7396 |  0.5271 |
| xgboost_v1      | test    |            6 |               1 | 1435 |  3.7099 | 10.1157 |  0.2245 |
| xgboost_v1      | test    |            6 |               2 | 1429 |  4.3682 | 10.4091 |  0.1815 |
| xgboost_v1      | test    |            6 |               3 | 1423 |  4.7826 | 10.7619 |  0.1282 |
| xgboost_v2      | test    |            1 |               1 | 1540 |  5.3088 |  7.7799 |  0.5928 |
| xgboost_v2      | test    |            1 |               2 | 1533 |  6.4220 |  8.9218 |  0.4654 |
| xgboost_v2      | test    |            1 |               3 | 1527 |  7.2356 | 10.1762 |  0.3043 |
| xgboost_v2      | test    |            2 |               1 | 1407 |  3.4817 |  5.2896 |  0.4970 |
| xgboost_v2      | test    |            2 |               2 | 1402 |  4.0444 |  6.0311 |  0.3432 |
| xgboost_v2      | test    |            2 |               3 | 1397 |  4.4658 |  6.4862 |  0.2353 |
| xgboost_v2      | test    |            3 |               1 |  974 |  5.0793 |  6.9887 |  0.3400 |
| xgboost_v2      | test    |            3 |               2 |  965 |  5.9168 |  7.8019 |  0.1606 |
| xgboost_v2      | test    |            3 |               3 |  957 |  6.3341 |  8.1812 |  0.0715 |
| xgboost_v2      | test    |            4 |               1 | 1404 |  5.7811 |  8.7305 |  0.5448 |
| xgboost_v2      | test    |            4 |               2 | 1390 |  6.7477 |  9.7758 |  0.4227 |
| xgboost_v2      | test    |            4 |               3 | 1380 |  7.2644 | 10.3776 |  0.3467 |
| xgboost_v2      | test    |            5 |               1 | 1169 |  3.7078 |  4.9241 |  0.7469 |
| xgboost_v2      | test    |            5 |               2 | 1164 |  4.7497 |  6.1825 |  0.6017 |
| xgboost_v2      | test    |            5 |               3 | 1159 |  5.3060 |  6.7993 |  0.5186 |
| xgboost_v2      | test    |            6 |               1 | 1435 |  3.7432 | 10.1575 |  0.2180 |
| xgboost_v2      | test    |            6 |               2 | 1429 |  4.4304 | 10.4842 |  0.1697 |
| xgboost_v2      | test    |            6 |               3 | 1423 |  4.7881 | 10.7887 |  0.1239 |

## G. V2 weather ablation

| model      | split      | Station_No   | horizon_hours   |     n |    mae |   rmse |     r2 |
|:-----------|:-----------|:-------------|:----------------|------:|-------:|-------:|-------:|
| xgboost_v2 | test       | ALL          | ALL             | 23655 | 5.2693 | 8.4237 | 0.4594 |
| xgboost_v2 | test       | ALL          | 1               |  7929 | 4.5206 | 7.6462 | 0.5567 |
| xgboost_v2 | test       | ALL          | 2               |  7883 | 5.3868 | 8.4747 | 0.4522 |
| xgboost_v2 | test       | ALL          | 3               |  7843 | 5.9081 | 9.0951 | 0.3676 |
| xgboost_v2 | validation | ALL          | ALL             | 25744 | 5.5951 | 9.0573 | 0.4198 |
| xgboost_v2 | validation | ALL          | 1               |  8603 | 4.6883 | 8.1662 | 0.5295 |
| xgboost_v2 | validation | ALL          | 2               |  8580 | 5.7165 | 9.0852 | 0.4158 |
| xgboost_v2 | validation | ALL          | 3               |  8561 | 6.3846 | 9.8463 | 0.3132 |

V2 did not improve pooled validation performance: MAE increased from 5.5771
(V1) to 5.5951 and RMSE increased from 8.9357 to 9.0573. V1 was therefore frozen
as the selected configuration before test access. The one-shot test evaluation
also showed higher error for V2, but that result was not used for selection.

Temperature and humidity are exact origin-time observations. Missing values are
median-imputed separately inside each horizon pipeline; medians are learned
from train only for validation and train+validation only for final test fitting.
Missing indicators are added. No row is dropped for weather missingness.

| fit_stage      |   horizon_hours |   fit_rows |   temperature_missing |   humidity_missing |   temperature_training_median |   humidity_training_median |
|:---------------|----------------:|-----------:|----------------------:|-------------------:|------------------------------:|---------------------------:|
| validation_fit |               1 |      34235 |                  2106 |               2106 |                       28.0933 |                    71.2800 |
| validation_fit |               2 |      33994 |                  2101 |               2101 |                       28.0883 |                    71.2667 |
| validation_fit |               3 |      33772 |                  2097 |               2097 |                       28.0833 |                    71.2826 |
| final_test_fit |               1 |      42838 |                  3664 |               3664 |                       28.0351 |                    70.3017 |
| final_test_fit |               2 |      42574 |                  3657 |               3657 |                       28.0300 |                    70.3017 |
| final_test_fit |               3 |      42333 |                  3651 |               3651 |                       28.0227 |                    70.3058 |

## H. Interpretability

Built-in gain importance:

| model      |   horizon_hours | feature                   |   importance |
|:-----------|----------------:|:--------------------------|-------------:|
| xgboost_v1 |               1 | history_time__pm25_lag_1h |       0.6593 |
| xgboost_v1 |               1 | history_time__pm25_lag_2h |       0.0532 |
| xgboost_v1 |               1 | history_time__hour        |       0.0487 |
| xgboost_v1 |               1 | history_time__pm25_lag_3h |       0.0452 |
| xgboost_v1 |               1 | history_time__month       |       0.0330 |
| xgboost_v1 |               1 | station__Station_No_4     |       0.0330 |
| xgboost_v1 |               1 | history_time__day_of_week |       0.0294 |
| xgboost_v1 |               1 | station__Station_No_3     |       0.0261 |
| xgboost_v1 |               1 | station__Station_No_1     |       0.0251 |
| xgboost_v1 |               1 | station__Station_No_6     |       0.0239 |
| xgboost_v1 |               2 | history_time__pm25_lag_1h |       0.5844 |
| xgboost_v1 |               2 | history_time__hour        |       0.0616 |
| xgboost_v1 |               2 | history_time__pm25_lag_2h |       0.0568 |
| xgboost_v1 |               2 | station__Station_No_4     |       0.0559 |
| xgboost_v1 |               2 | history_time__month       |       0.0451 |
| xgboost_v1 |               2 | station__Station_No_3     |       0.0397 |
| xgboost_v1 |               2 | station__Station_No_5     |       0.0387 |
| xgboost_v1 |               2 | history_time__pm25_lag_3h |       0.0326 |
| xgboost_v1 |               2 | station__Station_No_6     |       0.0321 |
| xgboost_v1 |               2 | station__Station_No_1     |       0.0265 |
| xgboost_v1 |               3 | history_time__pm25_lag_1h |       0.4327 |
| xgboost_v1 |               3 | history_time__pm25_lag_2h |       0.1304 |
| xgboost_v1 |               3 | history_time__hour        |       0.0780 |
| xgboost_v1 |               3 | station__Station_No_4     |       0.0602 |
| xgboost_v1 |               3 | station__Station_No_5     |       0.0598 |
| xgboost_v1 |               3 | history_time__month       |       0.0570 |
| xgboost_v1 |               3 | station__Station_No_6     |       0.0423 |
| xgboost_v1 |               3 | station__Station_No_3     |       0.0412 |
| xgboost_v1 |               3 | station__Station_No_1     |       0.0389 |
| xgboost_v1 |               3 | history_time__pm25_lag_3h |       0.0279 |

Mean absolute TreeSHAP values were computed on a deterministic sample of at most
500 locked-test rows per horizon after configuration was frozen. They are for
interpretation only and were not used to revise model selection.

| model      |   horizon_hours | feature                   |   mean_absolute_shap |   shap_sample_rows |
|:-----------|----------------:|:--------------------------|---------------------:|-------------------:|
| xgboost_v1 |               1 | history_time__pm25_lag_1h |               6.2427 |                500 |
| xgboost_v1 |               1 | history_time__hour        |               0.9840 |                500 |
| xgboost_v1 |               1 | history_time__month       |               0.6884 |                500 |
| xgboost_v1 |               1 | station__Station_No_4     |               0.4284 |                500 |
| xgboost_v1 |               1 | history_time__pm25_lag_2h |               0.2665 |                500 |
| xgboost_v1 |               1 | station__Station_No_3     |               0.2569 |                500 |
| xgboost_v1 |               1 | history_time__pm25_lag_3h |               0.2501 |                500 |
| xgboost_v1 |               1 | history_time__day_of_week |               0.2257 |                500 |
| xgboost_v1 |               1 | station__Station_No_5     |               0.2075 |                500 |
| xgboost_v1 |               1 | station__Station_No_1     |               0.0493 |                500 |
| xgboost_v1 |               2 | history_time__pm25_lag_1h |               5.6181 |                500 |
| xgboost_v1 |               2 | history_time__hour        |               1.2916 |                500 |
| xgboost_v1 |               2 | history_time__month       |               0.9053 |                500 |
| xgboost_v1 |               2 | station__Station_No_4     |               0.6107 |                500 |
| xgboost_v1 |               2 | station__Station_No_3     |               0.3703 |                500 |
| xgboost_v1 |               2 | history_time__day_of_week |               0.3539 |                500 |
| xgboost_v1 |               2 | station__Station_No_5     |               0.3408 |                500 |
| xgboost_v1 |               2 | history_time__pm25_lag_3h |               0.2242 |                500 |
| xgboost_v1 |               2 | history_time__pm25_lag_2h |               0.1846 |                500 |
| xgboost_v1 |               2 | station__Station_No_1     |               0.0648 |                500 |
| xgboost_v1 |               3 | history_time__pm25_lag_1h |               4.8588 |                500 |
| xgboost_v1 |               3 | history_time__hour        |               1.4618 |                500 |
| xgboost_v1 |               3 | history_time__month       |               1.1271 |                500 |
| xgboost_v1 |               3 | station__Station_No_4     |               0.8004 |                500 |
| xgboost_v1 |               3 | history_time__day_of_week |               0.4361 |                500 |
| xgboost_v1 |               3 | station__Station_No_5     |               0.4337 |                500 |
| xgboost_v1 |               3 | station__Station_No_3     |               0.4275 |                500 |
| xgboost_v1 |               3 | history_time__pm25_lag_2h |               0.3941 |                500 |
| xgboost_v1 |               3 | history_time__pm25_lag_3h |               0.2721 |                500 |
| xgboost_v1 |               3 | station__Station_No_1     |               0.0714 |                500 |

Importance and SHAP describe model behavior, not causal effects.

Across all horizons, PM2.5(t-1h) is the dominant feature. Its gain importance and
mean absolute SHAP contribution decrease with horizon, while calendar and
station contributions become relatively more prominent. This is consistent with
weakening short-term persistence, but it does not establish causal effects.

## I. Limitations of hourly HealthyAir data

- Predictions are validated only at exact hourly monitored-station timestamps.
- No minute-level ground truth, accuracy, or road-level concentration is claimed.
- Gaps reduce samples unevenly, and station observations do not directly measure
  road segments.
- The model covers only the six observed station identities and this historical
  period; generalization to roads, new monitors, or later years is unverified.
- Zero and extreme observations remain included. Audit IQR flags are metadata,
  not predictors or removal rules.
- Test results are now locked evidence and must not be used for iterative tuning.

## J. Requirements for finer temporal-resolution validation

Arrival-time-aware segment validation would require PM2.5 observations at the
temporal resolution of intended routing decisions (for example, genuine
minute-scale or appropriately frequent measurements), not interpolated hourly
labels. Required properties include:

- calibrated PM2.5 observations with documented units and quality control;
- synchronized clocks/time zones across pollution, weather, traffic, and route
  traversal records;
- continuous station/mobile-sensor operation sufficient to construct exact lags
  and targets without treating outages as observations;
- spatial coverage representative of roads and route microenvironments;
- an overlap period with HealthyAir where available for cross-instrument checks;
- documentation of sensor, season, traffic, land-use, and policy distribution
  shifts.

Newer data should first be treated as external temporal validation. It should not
be blindly merged into training until comparability, calibration, overlap, and
distribution shift have been assessed.

## K. Target-time forecasting API

```python
HourlyStationForecaster.predict_pm25(
    station_or_location,
    target_time,
    *,
    prediction_time,
    pm25_lags={1: ..., 2: ..., 3: ...},
    temperature=None,
    humidity=None,
) -> float
```

The API requires exact hourly prediction/target times and a 1–3 hour difference.
It currently accepts only known monitored stations. Unknown/geographic locations
are rejected explicitly: a future, separate spatial layer must translate road
locations into defensible concentration estimates. Routing and exposure logic
remain separate and unimplemented.

## L. Recommended Milestone 3

Before routing, design and validate the spatial-estimation layer and its
uncertainty using real station coordinates and defensible spatial covariates.
Define how a road location and arrival time will request a forecast without
claiming road-level direct measurement or sub-hourly accuracy. Do not use the
locked test set for further XGBoost tuning.

AIRPATH's intended direction is an arrival-time-aware, segment-level exposure
framework followed by route selection under a user-defined travel-time
constraint. No claim of being the first pollution-aware routing system is made.
