#!/usr/bin/env sh
set -eu

npm run lint --prefix frontend
npm run test:coverage --prefix frontend
printf '%s\n' '[PHASE10] frontend-tests-ok'
npm run build --prefix frontend
printf '%s\n' '[PHASE9] frontend-build-ok'
printf '%s\n' '[PHASE10] frontend-build-ok'
