; benchmark generated from python API
(set-info :status unknown)
(declare-fun n () Int)
(declare-fun q () Int)
(declare-fun k () Int)
(declare-fun out () (Array Int Int))
(declare-fun selected () Bool)
(assert
 (>= n 0))
(assert
 (>= q 0))
(assert
 (< q n))
(assert
 (let (($x115 (= (select (ite selected (store out n k) out) n) k)))
(let (($x116 (=> selected $x115)))
(let ((?x42 (+ n 1)))
(let ((?x75 (ite selected 1 0)))
(let ((?x140 (+ n ?x75)))
(let (($x43 (<= ?x140 ?x42)))
(let (($x41 (>= ?x140 n)))
(let ((?x95 (select out q)))
(let ((?x214 (store out n k)))
(let ((?x215 (ite selected ?x214 out)))
(let ((?x94 (select ?x215 q)))
(let (($x96 (= ?x94 ?x95)))
(let (($x117 (and $x96 $x41 $x43 $x116)))
(not $x117)))))))))))))))
(check-sat)
