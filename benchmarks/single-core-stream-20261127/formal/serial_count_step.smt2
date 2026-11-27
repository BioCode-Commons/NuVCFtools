; benchmark generated from python API
(set-info :status unknown)
(declare-fun new_count () Int)
(declare-fun old_count () Int)
(declare-fun delta () Int)
(assert
 (= old_count new_count))
(assert
 (>= old_count 0))
(assert
 (>= delta 0))
(assert
 (let ((?x348 (+ old_count delta)))
 (<= ?x348 9223372036854775807)))
(assert
 (let ((?x374 (+ new_count delta)))
(let ((?x348 (+ old_count delta)))
(let (($x377 (= ?x348 ?x374)))
(not $x377)))))
(check-sat)
