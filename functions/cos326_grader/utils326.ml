(* fst = correct; snd = total possible *)
type points = (int * int)



(* used to store output that is seen by the student *)
let report_chan : out_channel =
  try snd (Filename.open_temp_file ~mode:[Open_append] ~temp_dir:"/tmp" "cos326_report" "")
  with Sys_error _ -> raise (Sys_error "failed to create file")

(* same as Printf.printf, but outputs to report_chan and always flushes *)
let printf326 fmt =
  let ret = Printf.fprintf report_chan fmt in
  flush report_chan; ret

(* used to store output about intermediate progress that is used for grade
 * calculation and collection *)
let results_chan : out_channel =
  try snd (Filename.open_temp_file ~mode:[Open_append] ~temp_dir:"/tmp" "cos326_results" "")
  with Sys_error _ -> raise (Sys_error "failed to create file")

(* same as Printf.printf, but outputs to results_chan and always flushes *)
let rprintf326 fmt =
  let ret = Printf.fprintf results_chan fmt in
  flush results_chan; ret

(* returns the value associated with var in the process environment or the empty
 * string if var is unbound *)
let get_envvar (var : string) : string =
  match Sys.getenv_opt var with
  | None -> ""
  | Some v -> v



(* given a running tally and a new problem, return the adjusted tally *)
let tally (running : points) (this : bool) : points =
  let (rc, rt) = running in
  if this then
    (printf326 "--> passed\n"; flush stdout; (rc+1, rt+1))
  else
    (printf326 "--> FAILED\n"; flush stdout; (rc, rt+1))

(* so_far tracks correct problems
 * tally tracks passed tests in current problem
 * worth tracks awarded points for current problem *)
let count_prob (so_far : points) (tally : points) (worth : points) : points =
  let ((sc, st), (tc, tt)) = (so_far, tally) in
  let snippet_delim = "```" in
  let (n, d) = worth in
  if tc = tt then
    (
      rprintf326 "\n%s\nProblem passed (%d / %d points)\n%s\n" snippet_delim n d snippet_delim;
      printf326 "\n%s\nProblem passed (%d / %d points)\n%s\n" snippet_delim n d snippet_delim;
      flush stdout;
      (sc+1, st+1)
    )
  else
    (
      rprintf326 "\n%s\nProblem FAILED (%d / %d points)\n%s\n" snippet_delim n d snippet_delim;
      printf326 "\n%s\nProblem FAILED (%d / %d points)\n%s\n" snippet_delim n d snippet_delim;
      flush stdout;
      (sc, st+1)
    )

(* so_far tracks correct optional problems
 * tally tracks passed tests in current optional problem
 * worth tracks awarded points for current optional problem *)
let count_prob_opt (so_far : points) (tally : points) (worth : points) : points =
  let ((sc, st), (tc, tt)) = (so_far, tally) in
  let snippet_delim = "```" in
  let (n, d) = worth in
  if tc = tt then
    (
      rprintf326 "\n%s\nOptional problem passed (%d / %d points)\n%s\n" snippet_delim n d snippet_delim;
      printf326 "\n%s\nOptional problem passed (%d / %d points)\n%s\n" snippet_delim n d snippet_delim;
      flush stdout;
      (sc+1, st+1)
    )
  else
    (
      rprintf326 "\n%s\nOptional problem FAILED (%d / %d points)\n%s\n" snippet_delim n d snippet_delim;
      printf326 "\n%s\nOptional problem FAILED (%d / %d points)\n%s\n" snippet_delim n d snippet_delim;
      flush stdout;
      (sc, st+1)
    )



(* compare two lists of things and ensure that they contain the same contents,
 * irrespective of order *)
let one_to_one stu ans =
  List.for_all (fun s -> List.mem s ans) stu
  &&
  List.for_all (fun a -> List.mem a stu) ans
  &&
  List.length stu = List.length ans

(* compare floats down to the point of floating point figments *)
let cmp_float (f1 : float) (f2 : float) : bool =
  let d = f1 -. f2 in
  abs_float d < 0.0000000001



(* given a check and a message, if the check fails print the message.
 * in either case, return the result of the check *)
let assert326 (cond : bool) (msg : string) : bool =
  if not cond then printf326 "> %s " msg;
  flush stdout;
  cond

(* given student result, intended result, a comparison function, and a message:
 * if student result is "None", that means that they threw an exception or some
 * other unexpected behavior, and fail the test.
 * otherwise, extract the actual result from the option, compare it with the intended
 * if they're the same, pass the test
 * if not the same, print the message and fail the test *)
let assert326' (res : 'a option) (right : 'b) (cmp : 'a -> 'b -> bool) (msg : string) : bool =
  match res with
  | None -> (printf326 "> %s " msg; flush stdout; false)
  | Some x ->
      if cmp x right
      then true
      else (printf326 "> %s " msg; flush stdout; false)



let print_header (prob : string) : unit =
  printf326 "\n### %s\n\n" prob;
  flush stdout

(* in-line test description *)
let print_check (prob : string) : unit =
  printf326 "> %s\t" prob;
  flush stdout

(* space-separated note for student or grader *)
let print_note (note : string) : unit =
  printf326 "**%s**\n\n" note;
  flush stdout

(* string_of_list, taking string_of_(payloadtype) as an argument*)
let printer (f) (xs) : string =
  let rec print_list (f) (xs) : string =
    match xs with
    | [] -> "]"
    | [hd] -> (f hd) ^ "]"
    | hd::tl -> (f hd) ^ "; " ^ (print_list f tl)
  in
  "[" ^ print_list f xs

(* alias for string_of_{int,char,float,bool,string} *)
let pi = Printf.sprintf "%d"
let pc = Printf.sprintf "%c"
let pf = Printf.sprintf "%f"
let pb = Printf.sprintf "%B"
let ps = Printf.sprintf "%s"

(* string_of_option, taking string_of_(payloadtype) as an argument*)
let po f x =
  match x with
  | None -> "None"
  | Some v -> "Some " ^ (f v)

(* string_of_{int,char,float,bool,string}_option *)
let pio = po pi
let pco = po pc
let pfo = po pf
let pbo = po pb
let id x = x
let pso = po id

(* string_of_{int,char,float,bool,string}_list *)
let print_il = printer (pi)
let print_cl = printer (pc)
let print_fl = printer (pf)
let print_bl = printer (pb)
let print_sl = printer (ps)

(* string_of_{int,char}_list_list *)
let print_ill = printer (printer (pi))
let print_cll = printer (printer (pc))

(* string_of_{int,char}_list_list_list *)
let print_illl = printer ( printer (printer (pi)))
let print_clll = printer ( printer (printer (pc)))

(* failure message: for use with assert326'
   takes a print function for payload type
   and an option (None: there was an exception
   thrown, so no value is available; Some x:
   return string of the extracted x value
*)
let fm pf o =
  match o with
  | None -> "None"
  | Some x -> pf x

(* text wrapper *)
let wrap width s =
  let whitespace_chars =
    String.concat ""
      (List.map (String.make 1)
        [
          Char.chr 9;  (* HT *)
          Char.chr 10; (* LF *)
          Char.chr 11; (* VT *)
          Char.chr 12; (* FF *)
          Char.chr 13; (* CR *)
          Char.chr 32; (* space *)
        ])
  in
  let space = "[" ^ whitespace_chars ^ "]+" in
  let s' = Str.global_replace (Str.regexp space) " " s in
  let l = Str.split (Str.regexp space) s' in
  Format.pp_set_margin Format.str_formatter width;
  Format.pp_open_box Format.str_formatter 0;
  List.iter
    (fun x ->
      Format.pp_print_string Format.str_formatter x;
      Format.pp_print_break Format.str_formatter 1 0;) l;
  Format.flush_str_formatter ()

let wwrap = wrap 68



(* Catch runaway operations *)
exception Timeout
(* start a timer that will raise Timeout after !t seconds *)
let timeout t =
  Sys.set_signal Sys.sigalrm (Sys.Signal_handle (fun i -> raise Timeout));
  ignore (Unix.setitimer Unix.ITIMER_REAL {Unix.it_interval=0.; Unix.it_value= !t})
(* cancel the timer *)
let timein () = ignore (Unix.setitimer Unix.ITIMER_REAL {Unix.it_interval=0.; Unix.it_value=0.})
(* a reference to pass to timeout *)
let timelimit = ref 1.
(* a setter for the reference to pass to timeout *)
let set_timelimit t =
  timelimit := t

let contains s1 s2 =
    let re = Str.regexp_string s2
    in
        try ignore (Str.search_forward re s1 0); true
        with Not_found -> false

let rec read_due_date (n : int) (open_file) =
  if n > 1 then  let _ = input_line open_file in read_due_date (n-1) (open_file)
  else input_line open_file

let convert_to_epoch (s:string) =
  let year = int_of_string(String.sub s 0 4) - 1900 in
  let month = int_of_string(String.sub s 4 2) - 1 in
  let day = int_of_string(String.sub s 6 2) in
  let hour = int_of_string(String.sub s 8 2) in
  {Unix.tm_sec = 59; Unix.tm_min = 59; Unix.tm_hour = hour; Unix.tm_mday = day; Unix.tm_mon = month; Unix.tm_year = year; Unix.tm_wday = 1; Unix.tm_yday = month * 31 + day; Unix.tm_isdst = false}

let fix s =
  let s1 = String.map (fun c -> if c=='@'||c=='&'||c==','||c==';'||c==':'||c=='"' then ' ' else c) s in
  String.trim (String.lowercase_ascii s1)

let detect_partners () =
  let ic = open_in "README.txt" in
  let rec find_part u =
    try
    let line = input_line ic in
    if contains line "Partner 2's login:" then
    let s2 = (fix (String.sub line 17 ((String.length line)-17))) in
    if String.length s2 > 2 then let _ = Printf.printf "partner: %s \n" s2 in Some s2 else None
    else find_part ()
    with e -> None
  in
  let par_uid = find_part () in
  close_in ic;
  par_uid

let extensions (n : int) (uid : string) =
   let extend_file = String.concat "" ["/u/cos326/Weekly/Lists/extensions_a"; (string_of_int n)] in
   let ic = open_in extend_file in
   let rec check_ex s =
   try
     let line = input_line ic in
     if contains line s then
     let len = String.index line ' ' in
     int_of_string (String.trim (String.sub line len ((String.length line) - len)))
     else check_ex s
   with e -> 0
   in
   let exten = check_ex uid in
   close_in ic;
   exten

let get_late_days (n: int) (uid : string) (days_late : int) =
  let late_file = "/u/cos326/Weekly/Lists/used_late_days" in
  let s1 = String.concat "" ["sed -i '/"; uid; " "; (string_of_int n); "/d' /u/cos326/Weekly/Lists/used_late_days"] in
  let _ = Sys.command s1 in
  let ic = open_in late_file in
  let rec check_late s n =
     try
     let line = input_line ic in
     if contains line s then
     let len = (String.length line) - 2 in
     check_late s ((int_of_string (String.trim (String.sub line len 2)))+n)
     else check_late s n
     with e -> n
   in
   let days = check_late uid 0 in
   close_in ic;
   days

let add_late_days (days : int) (a : int) (uid : string) =
  let s = String.concat "" ["echo '"; uid; " "; (string_of_int a); " "; (string_of_int days); "' >> /u/cos326/Weekly/Lists/used_late_days"] in
  let _ = Sys.command s in
  ()

let print_late_days (a_num : int) (total_points : int) (a_name : string list) (uid : string) =
  let due_file = "/u/cos326/Grading/duetimes" in
  let ic = open_in due_file in
  let partner = if a_num == 7 || a_num == 5 then detect_partners () else None in
  let due_date =
  try
    let line = read_due_date a_num ic in  (* read line from in_channel and discard \n *)
    close_in ic;                 (* close the input channel *)
    (fst (Unix.mktime (convert_to_epoch line)))
  with e ->                      (* some unexpected exception occurs *)
    close_in_noerr ic;           (* emergency closing *)
    0.0
  in
  let rec get_time files=
    match files with
    a::b -> let file_stats = Unix.stat ("/u/cos326/tigerfile/Assignment_"^(string_of_int a_num)^"/by_netid/"^uid^"/"^a) in
    let file_tail = get_time b in
    let mtime = file_stats.st_mtime in
    if mtime > file_tail then mtime else file_tail
    | [] -> 0.0 in

  let late_time = ((get_time a_name) -. due_date) in
  let days_late = int_of_float (late_time/.86400.0) in
  let hours_late = ((int_of_float late_time)/3600) mod 24 in
  if late_time > 7200.0 then
    let extension = (match partner with
    | Some x -> max (extensions a_num uid) (extensions a_num x)
    | None -> (extensions a_num uid)
    ) in
    let late_days = 4 - (match partner with
    | Some x -> min (get_late_days a_num uid (days_late-extension)) (get_late_days a_num x (days_late-extension))
    | None -> (get_late_days a_num uid (days_late-extension))
    ) in
    Printf.printf "Assignment submitted %d days and %d hours late\n" days_late hours_late;
    let _= Printf.printf"avalible late days: %d\n" late_days in
    let _ = if extension > 0 then Printf.printf "Extension of %d days given\n" extension else () in
    let penalty = if days_late < 4 + extension then (4 + extension) - days_late else 0 in
    let penalty = if days_late < 4 + extension + late_days && late_days > 0 then
      let late_days = if penalty + late_days > 5 then 5 - penalty else late_days in
      let _ = Printf.printf "%d late days used\n" (late_days) in
      add_late_days late_days a_num uid;
      (penalty + late_days)
      else penalty in
    Printf.printf "Late penalty: %d percent, %d points deducted\n" ((5-penalty)*20) (total_points - ((total_points * penalty) / 5))
  else ()

