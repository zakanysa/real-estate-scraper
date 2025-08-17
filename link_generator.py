def generate_oc_link(
    jelleg="lakas",
    ertekesites="elado",
    ar_min=None,
    ar_max=None,
    elhelyezkedes=None,
    meret_min=None,
    meret_max=None,
    szoba_min=None,
    szoba_max=None
):
    base_url = "https://www.oc.hu/ingatlanok/lista"
    parts = []

    # Kötelező paraméterek
    if jelleg:
        parts.append(f"jelleg:{jelleg}")

    parts.append(f"ertekesites:{ertekesites}")

    # Opcionális paraméterek
    if ar_min and ar_max:
        parts.append(f"ar:{ar_min}~{ar_max}")
    elif ar_min:
        parts.append(f"ar:{ar_min}~")
    elif ar_max:
        parts.append(f"ar:~{ar_max}")

    if elhelyezkedes:
        parts.append(f"elhelyezkedes:{elhelyezkedes}")

    if meret_min and meret_max:
        parts.append(f"meret:{meret_min}~{meret_max}")
    elif meret_min:
        parts.append(f"meret:{meret_min}~")
    elif meret_max:
        parts.append(f"meret:~{meret_max}")

    if szoba_min and szoba_max:
        parts.append(f"szoba:{szoba_min}~{szoba_max}")
    elif szoba_min:
        parts.append(f"szoba:{szoba_min}~")
    elif szoba_max:
        parts.append(f"szoba:~{szoba_max}")

    # Link összeállítása
    full_url = base_url + "/" + ";".join(parts)
    print(full_url)
    return full_url
