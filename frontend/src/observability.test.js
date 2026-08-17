import test from 'node:test'
import assert from 'node:assert/strict'
import { BROWSER_MARKERS, markBrowser } from './observability.js'

test('browser markers are stable and contain no sensitive values', () => {
  const output = []
  markBrowser('AUTH_RESTORED', value => output.push(value))
  markBrowser('MEDIA_READY', value => output.push(value))
  assert.deepEqual(output, [BROWSER_MARKERS.AUTH_RESTORED, BROWSER_MARKERS.MEDIA_READY])
  assert.ok(output.every(value => !/token|secret|audio|password/i.test(value)))
})
