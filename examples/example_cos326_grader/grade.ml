open Utils326

let probs_right : points = (0, 0)
let opt_probs_right : points = (0, 0)
let opt_total_points : points = (0, 0)

let _ =
  rprintf326 "Max problems: %d\n" 1;
  rprintf326 "Max points: %d\n" 1;
  rprintf326 "Max pending: %d\n" 0;
  rprintf326 "Max optional problems: %d\n" 0;
  rprintf326 "Max optional points: %d\n" 0;
  rprintf326 "Max optional pending: %d\n" 0

let prob1 = "Problem 1 unimplemented"

open A1

let _ = print_header "Problem 1"
let total = (0, 0)

let total = tally total (assert326 (prob1 = "Hello World!") "1 does not print correct message")
let probs_right = count_prob probs_right total (fst total, 1)
