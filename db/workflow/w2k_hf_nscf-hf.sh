#!/usr/bin/env bash
#
# This is a test script to get non-scf HF band gap using WIEN2k
#
mkdir -p diamond
cp diamond.struct diamond
cd diamond || exit 1
# use 12x12x12 for SCF such that 2c 3c 4c 6c meshes of HF are allowed
init_lapw -b -numk 1728
sed -i '1s/.*.*/TOT EX_LDA VX_LDA/' diamond.in0
run_lapw -ec 0.00000001
save_lapw -d lda
#init_hf_lapw

cat > diamond.inhf << EOF
1.00         alpha
F            screened (T) or unscreened (F)
8            nband
6            gmax
3            lmaxe
3            lmaxv
1d-3         tolu
EOF

cp diamond.in0 diamond.in0_grr
sed -i '1s/.*.*/KXC EX_SLDA VX_SLDA/' diamond.in0_grr
sed -i 's/NR2V/R2V/' diamond.in0_grr

sed -i 's/  0  /  1  /' diamond.inc

for k in 2 3 4 6; do
  if [ -d "hf-k$k" ]; then
    continue
  fi
  printf "1728\n$k\n$k\n$k\n" | run_kgenhf_lapw -redklist
  run_lapw -hf -redklist -diaghf -nonself
  save_lapw -d hf-k$k
  rm -f *.broyd*
done
