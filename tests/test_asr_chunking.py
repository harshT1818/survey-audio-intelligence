from src.asr.chunking import (
    ASRChunk,
    merge_asr_chunks,
    remove_repeated_overlap,
)


def test_exact_overlap_is_removed():
    previous = (
        "क्या आप राज्य सरकार में बदलाव"
    )

    current = (
        "राज्य सरकार में बदलाव "
        "देखना चाहते हैं या नहीं"
    )

    result = remove_repeated_overlap(
        previous_text=previous,
        current_text=current,
    )

    assert (
        result
        == "देखना चाहते हैं या नहीं"
    )


def test_no_overlap_keeps_full_text():
    previous = (
        "क्या आप उत्तर प्रदेश के निवासी है"
    )

    current = (
        "हाँ ठीक है अगला सवाल"
    )

    result = remove_repeated_overlap(
        previous_text=previous,
        current_text=current,
    )

    assert (
        result
        == "हाँ ठीक है अगला सवाल"
    )


def test_single_word_overlap_is_removed():
    previous = (
        "आप राज्य सरकार"
    )

    current = (
        "सरकार में बदलाव चाहते हैं"
    )

    result = remove_repeated_overlap(
        previous_text=previous,
        current_text=current,
    )

    assert (
        result
        == "में बदलाव चाहते हैं"
    )


def test_chunks_are_sorted_before_merging():
    chunks = [
        ASRChunk(
            chunk_id="chunk_01",
            start_sec=15,
            end_sec=32,
            text=(
                "सरकार में बदलाव "
                "देखना चाहते हैं"
            ),
        ),
        ASRChunk(
            chunk_id="chunk_00",
            start_sec=0,
            end_sec=17,
            text=(
                "क्या आप राज्य सरकार"
            ),
        ),
    ]

    result = merge_asr_chunks(
        chunks
    )

    assert result.start_sec == 0
    assert result.end_sec == 32

    assert (
        result.text
        == (
            "क्या आप राज्य सरकार "
            "में बदलाव देखना चाहते हैं"
        )
    )


def test_realistic_prompting_chunks_merge():
    chunks = [
        ASRChunk(
            chunk_id="chunk_00",
            start_sec=0,
            end_sec=17,
            text=(
                "क्या आप राज्य सरकार"
            ),
        ),
        ASRChunk(
            chunk_id="chunk_01",
            start_sec=15,
            end_sec=32,
            text=(
                "राज्य सरकार में बदलाव देखना चाहते हैं "
                "या नहीं मुझे पता नहीं हाँ बोल दीजिए हाँ"
            ),
        ),
    ]

    result = merge_asr_chunks(
        chunks
    )

    assert (
        "मुझे पता नहीं"
        in result.text
    )

    assert (
        "हाँ बोल दीजिए"
        in result.text
    )

    assert (
        result.text.count(
            "राज्य सरकार"
        )
        == 1
    )


def test_empty_chunks_return_empty_window():
    result = merge_asr_chunks(
        []
    )

    assert result.start_sec == 0
    assert result.end_sec == 0
    assert result.text == ""