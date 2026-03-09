"""
Feature 1: Advanced Name-to-Username Generator
Permutasi lengkap dari nama asli ke kemungkinan username.
"""
import re
from typing import List, Set


class NameToUsernameGenerator:
    SEPARATORS    = ["", ".", "_", "-"]
    NUM_SUFFIXES  = ["1", "2", "99", "01", "123"]
    WORD_SUFFIXES = ["official", "id", "real"]

    def __init__(self, add_numbers=True, add_word_suffixes=True, max_variants=50):
        self.add_numbers      = add_numbers
        self.add_word_suffixes= add_word_suffixes
        self.max_variants     = max_variants

    def generate(self, full_name: str) -> List[str]:
        raw = full_name.strip()
        if " " not in raw:
            return self._handle_existing(raw)

        parts = [p.lower() for p in re.split(r"\s+", raw) if p]
        if not parts:
            return [raw.lower()]

        bag: Set[str] = set()

        # 1. Full combinations with each separator
        for sep in self.SEPARATORS:
            bag.add(sep.join(parts))              # budisantoso / budi.santoso …
        # Reversed
        rev = list(reversed(parts))
        for sep in [".", "_"]:
            bag.add(sep.join(rev))               # santoso.budi

        if len(parts) >= 2:
            first, last = parts[0], parts[-1]
            fi, li      = first[0], last[0]

            # 2. Initial combos
            for sep in ["", ".", "_"]:
                bag.add(fi + sep + last)         # bsantoso / b.santoso / b_santoso
                bag.add(first + sep + li)        # budis / budi.s / budi_s

            # 3. Truncated (min 3 chars kept per part)
            for n in [3, 4, 5]:
                if len(first) > n:
                    t = first[:n]
                    for sep in ["", ".", "_"]:
                        bag.add(t + sep + last)  # budsantoso / bud.santoso
                if len(last) > n:
                    t = last[:n]
                    for sep in ["", ".", "_"]:
                        bag.add(first + sep + t) # budi.san / budisant

        # 4. Augment clean bases only
        clean_bases = sorted([b for b in bag if re.match(r"^[a-z0-9]{5,14}$", b)], key=len)[:8]
        for base in clean_bases:
            if self.add_numbers:
                for sfx in self.NUM_SUFFIXES:
                    bag.add(base + sfx)
            if self.add_word_suffixes:
                bag.add(base + ".official")

        return self._rank_and_clean(bag)

    def _handle_existing(self, username: str) -> List[str]:
        variants: Set[str] = {username}
        clean = re.sub(r"[._\-]", "", username)
        variants.add(clean)
        if self.add_numbers:
            for sfx in self.NUM_SUFFIXES:
                variants.add(clean + sfx)
        return self._rank_and_clean(variants)

    def _rank_and_clean(self, variants: Set[str]) -> List[str]:
        out, seen = [], set()
        for v in variants:
            v = v.lower().strip()
            v = re.sub(r"[^\w.\-]", "", v)
            # Minimum 4 chars, max 30, no standalone single-char initials like "b_s"
            if not v or len(v) < 4 or len(v) > 30:
                continue
            if v in seen:
                continue
            seen.add(v)
            out.append(v)

        def score(s):
            pts = 0.0
            pts += len(s) * 0.15               # shorter = better
            # Full joined name gets bonus
            if not re.search(r"[._\-]", s):
                pts -= 1.0                     # joined has slight priority boost
            # Separator = realistic
            if re.search(r"[._\-]", s) and len(s) >= 6:
                pts -= 0.5
            # Trailing digit = lower priority
            if s[-1].isdigit():
                pts += 2.0
            if "official" in s:
                pts += 3.0
            return pts

        out.sort(key=score)
        return out[:self.max_variants]


# ─── Convenience ───────────────────────────────────────────────────────────

def generate_variants(name: str, max_variants: int = 40, add_numbers: bool = True) -> List[str]:
    return NameToUsernameGenerator(add_numbers=add_numbers,
                                   max_variants=max_variants).generate(name)

def is_full_name(text: str) -> bool:
    return " " in text.strip()

def sanitize_for_filename(text: str) -> str:
    return re.sub(r"[^\w\-.]", "_", text.strip()).strip("_")


if __name__ == "__main__":
    for name in ["Budi Santoso", "mutiara antika", "john doe", "johndoe"]:
        vs = generate_variants(name, max_variants=20)
        print(f"\n'{name}' → {len(vs)} variants:")
        for i, v in enumerate(vs, 1):
            print(f"  {i:>2}. {v}")
