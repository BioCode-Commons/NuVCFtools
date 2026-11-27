; benchmark generated from python API
(set-info :status unknown)
(declare-fun k2 () String)
(declare-fun k1 () String)
(declare-fun validation (String String) String)
(declare-fun context () String)
(assert
 (= k1 k2))
(assert
 (let ((?x716 (validation context k1)))
 (= ?x716 "")))
(assert
 (let ((?x195 (validation context k2)))
(let (($x196 (= ?x195 "")))
(not $x196))))
(check-sat)
