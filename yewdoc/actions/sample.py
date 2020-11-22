def sample_handler(doc, store, remote):
    if doc.name.startswith("-"):
        new_name = doc.name[1:]
        print(f"Sample: {doc.name}, {new_name}")
        #  store.rename_doc(doc, new_name)
