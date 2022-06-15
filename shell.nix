{
  pkgs ? import <nixpkgs> {},
  snapfaasSha256 ? "sha256-h0cJO/waluEkGEOku1MUPzRI6HvZlC/AkutgrT9NQW0=",
  snapfaasRev ? "61c4bff408adb466ee2714f9a0a82c25acf9bdf0",
  snapfaasSrc ? pkgs.fetchFromGitHub {
    owner = "princeton-sns";
    repo = "snapfaas";
    rev = snapfaasRev;
    sha256 = snapfaasSha256;
  },
  release ? false
}:

with pkgs;
let
  snapfaas = (import snapfaasSrc { inherit pkgs release; }).snapfaas;
in mkShell {
  buildInputs = [ lkl snapfaas lmdb gnumake e2fsprogs ];
  shellHook = ''
    # Mark variables which are modified or created for export.
    set -a
    source ${toString ./.env}
    set +a
  '';
}
