"""Pre-compute revision-2 feature caches (axis features, rotated copies, slow features)."""
from ..features.extra import build_features

TEST_ROT_SEED, TRAIN_ROT_SEED = 777, 555

if __name__ == "__main__":
    build_features("axis")
    build_features("axis", rotate_seed=TEST_ROT_SEED)
    build_features("axis", rotate_seed=TRAIN_ROT_SEED)
    for Ls in (4, 6, 8):
        build_features("slow", Ls=Ls)
    print("features built")
