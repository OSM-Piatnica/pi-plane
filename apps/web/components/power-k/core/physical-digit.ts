/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Digit printed on a key of the top row in the US layout ("Digit2" -> "2") */
const digitForCode = (code: string): string | undefined => /^Digit([0-9])$/.exec(code)?.[1];

/**
 * The key to append to a pending key sequence.
 *
 * On layouts where the digit row types other characters without Shift (French AZERTY: `&é"'`,
 * Czech: `+ěšč`, Slovak), a sequence that ends in a digit, such as `g1`, could never be typed:
 * Shift cancels a pending sequence. So when the character of the pressed key neither completes
 * nor continues a sequence, and the key is a top-row digit key whose digit does complete one,
 * the digit is used. Sequences that the typed character serves are never affected, and a key
 * pressed with no sequence pending is left alone, so single-key shortcuts are not changed.
 */
export const resolveSequenceKey = (
  sequenceMap: ReadonlyMap<string, string>,
  pendingSequence: string,
  key: string,
  code: string
): string => {
  if (!pendingSequence) return key;
  const digit = digitForCode(code);
  if (!digit || digit === key) return key;

  const typed = pendingSequence + key;
  for (const sequence of sequenceMap.keys()) {
    if (sequence.startsWith(typed)) return key;
  }
  return sequenceMap.has(pendingSequence + digit) ? digit : key;
};
