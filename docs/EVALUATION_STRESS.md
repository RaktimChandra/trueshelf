# Stress tests

## 1. Unseen room-naming style

A sixth supplier, "NOVA", was added only for this test. It names 2,540 rooms in French ("Chambre Supérieure Lit King Vue Mer"),
in marketing language ("Signature King Panoramic Sea") or with opaque codes ("Room Type C"). The room grammar was never written for these names.

| | Precision | Recall | F1 | Wrong merges |
|---|---|---|---|---|
| Known supplier styles only | 1.0000 | 1.0000 | 1.0000 | 0 |
| With the unseen NOVA style added | 1.0000 | 0.4855 | 0.6536 | 0 |

The grammar recognised a room class in 44% of NOVA names. Recall drops because rooms it cannot fully read stay unmatched.
Precision does not drop, so the system **fails safe**: an unknown name becomes a separate room that a person can map, not a wrong merge
that sells the wrong bed. Unreadable names are where a learned matcher (Round 2) or the Review Desk takes over.

*How this test changed the code:* its first run found 644 wrong merges. Names the grammar could only partly read
("Room Type B", "Junior Suite Lit King Côté Cour") were being grouped on the parts it did read. The fix is that any name with a
missing class, a missing bed or leftover words that were not understood is kept on its own and flagged for mapping.

## 2. Throughput (one CPU core, Python, unoptimised)

Bangkok held-out: 605 supplier hotel records → 37,835 candidate pairs.
Blocking and features took 0.52s; scoring took 0.524s
(about 72,169 pairs/s for scoring).

Matching is local to a city (blocking never compares hotels in different cities), so work grows with the size of each city,
not with the global catalogue. That makes it shard by destination: re-matching only cities whose feeds changed is an incremental job,
not a nightly global batch.
