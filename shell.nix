{
  pkgs ? import <nixpkgs> {},
  snapfaasSha256 ? "sha256-ZJS7GDW7lBILrMKrKXxLAw5gjKunSai27RO3oZvJAn4=",
  snapfaasRev ? "9791be9d108dd45abf50d9a62681d7a0f61613d5",
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
  snapfaas = (import snapfaasSrc { inherit pkgs release; });
in mkShell {
  buildInputs = [ lkl snapfaas.snapfaas snapfaas.webhook lmdb gnumake e2fsprogs ];
  shellHook = ''
    # Mark variables which are modified or created for export.
    set -a
    source ${toString ./.env}
    set +a
  '';
}
