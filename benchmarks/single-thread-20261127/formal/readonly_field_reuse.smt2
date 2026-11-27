; benchmark generated from python API
(set-info :status unknown)
(declare-fun y () String)
(declare-fun x () String)
(declare-fun decode (String String) Int)
(declare-fun context () String)
(assert
 (= x y))
(assert
 (let (($x62 (= (decode context x) (decode context y))))
(not $x62)))
(check-sat)
