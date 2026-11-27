; benchmark generated from python API
(set-info :status unknown)
(declare-fun byte () Int)
(assert
 (>= byte 0))
(assert
 (<= byte 255))
(assert
 (let ((?x67 (seq.unit (ite (= byte 13) 10 byte))))
(let ((?x25 (seq.unit byte)))
(let ((?x23 (seq.unit 10)))
(let (($x19 (= byte 13)))
(let ((?x309 (ite $x19 ?x23 ?x25)))
(let (($x69 (= ?x309 ?x67)))
(not $x69))))))))
(check-sat)
