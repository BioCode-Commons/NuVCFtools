; benchmark generated from python API
(set-info :status unknown)
(declare-fun field () (Seq Int))
(declare-fun tail () (Seq Int))
(assert
 (= (seq.indexof field (seq.unit 58) 0) (- 1)))
(assert
 (let ((?x10 (seq.++ field (seq.++ (seq.unit 58) tail))))
(let ((?x20 (seq.len ?x10)))
(let ((?x8 (seq.unit 58)))
(let ((?x12 (seq.indexof ?x10 ?x8 0)))
(let ((?x19 (+ ?x12 1)))
(let ((?x21 (seq.extract ?x10 ?x19 ?x20)))
(let (($x22 (= ?x21 tail)))
(let (($x17 (= (seq.extract ?x10 0 ?x12) field)))
(let (($x23 (and $x17 $x22)))
(not $x23)))))))))))
(check-sat)
