; benchmark generated from python API
(set-info :status unknown)
(declare-fun j () Int)
(declare-fun i () Int)
(declare-fun kj () Int)
(declare-fun ki () Int)
(declare-fun between () Int)
(declare-fun ri () Int)
(declare-fun rj () Int)
(assert
 (< i j))
(assert
 (< ki kj))
(assert
 (>= between 1))
(assert
 (let ((?x51 (+ ri between)))
 (= rj ?x51)))
(assert
 (let (($x35 (< ki kj)))
(let (($x53 (< ri rj)))
(let (($x54 (and $x53 $x35)))
(not $x54)))))
(check-sat)
