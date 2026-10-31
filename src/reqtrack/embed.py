def local(model):
    from fastembed import TextEmbedding

    m = TextEmbedding(model)

    def embed(texts):
        return [list(v) for v in m.embed(texts)]

    return embed
