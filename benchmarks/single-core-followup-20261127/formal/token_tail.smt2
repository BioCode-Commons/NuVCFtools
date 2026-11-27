; benchmark generated from python API
(set-info :status unknown)
(declare-fun last_field () (Seq Int))
(assert
 (let (($x43 (= (seq.extract last_field 0 (seq.len last_field)) last_field)))
(not $x43)))
(check-sat)
