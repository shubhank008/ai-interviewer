import test from 'node:test'
import assert from 'node:assert/strict'
import { MAX_RESUME_BYTES, setupValidation, validateResume } from './api.js'

test('setup validation requires job description and supported mode', () => {
  const result = setupValidation('', 'unknown', null)
  assert.equal(result.valid, false)
  assert.match(result.errors.jobDescription, /job description/)
  assert.match(result.errors.mode, /mode/)
})

test('resume validation accepts a PDF at the product limit', () => {
  assert.deepEqual(validateResume({ type: 'application/pdf', size: MAX_RESUME_BYTES }), { valid: true, error: '' })
  assert.equal(validateResume({ type: 'text/plain', size: 10 }).valid, false)
  assert.equal(validateResume({ type: 'application/pdf', size: MAX_RESUME_BYTES + 1 }).valid, false)
})
