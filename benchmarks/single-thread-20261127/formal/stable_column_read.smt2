; benchmark generated from python API
(set-info :status unknown)
(declare-fun B () (Array Int String))
(declare-fun A () (Array Int String))
(declare-fun i () Int)
(assert
 (= A B))
(assert
 (let ((?x10 (select B i)))
(let ((?x9 (select A i)))
(let (($x11 (= ?x9 ?x10)))
(not $x11)))))
(check-sat)
