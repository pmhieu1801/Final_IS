"""BioVault's integrated Streamlit UI, based on the M1 application."""

import os
from pathlib import Path
import sqlite3

import streamlit as st

from biovault.contracts import VaultRecord
from biovault.crypto.adapter import BasisCrypto
from biovault.demonstrations import SAMPLE_PATH, SCENARIOS, evaluate, run_scenario
from biovault.orchestrator import AppWorkflow
from biovault.storage import DATABASE_NAME, VaultConfigurationError, open_local_vault
from biovault.theme import CSS
from biovault.validation import UserInputError

PAGES = ("Dashboard", "Protect Image", "My Vault", "Reconstruction", "Security Lab", "Evaluation")
DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"


@st.cache_resource(show_spinner=False)
def services(directory: Path) -> AppWorkflow:
    return AppWorkflow(BasisCrypto(), open_local_vault(directory))


def clear_protection() -> None:
    st.session_state.pop("protect_result", None)
    st.session_state.pop("protect_saved", None)
    st.session_state.pop("protect_error", None)


def clear_protect_input() -> None:
    clear_protection()
    st.session_state["protect_sample"] = False
    st.session_state["protect_upload_id"] = st.session_state.get("protect_upload_id", 0) + 1


def clear_recovery() -> None:
    st.session_state.pop("last_recovery", None)


def clear_recovery_input() -> None:
    clear_recovery()
    st.session_state["recover_upload_id"] = st.session_state.get("recover_upload_id", 0) + 1


def change_page() -> None:
    clear_protection()
    clear_recovery()


def navigate(page: str, pair_id: str | None = None) -> None:
    change_page()
    st.session_state["navigation"] = page
    if pair_id is not None:
        st.session_state["recovery_target"] = pair_id


def record_label(record: VaultRecord) -> str:
    return f"{record.display_name} · {record.pair_id[:12]}"


def save_protection(workflow: AppWorkflow) -> None:
    result = st.session_state["protect_result"]
    try:
        workflow.save(result)
    except UserInputError as exc:
        st.session_state["protect_error"] = str(exc)
    except (OSError, sqlite3.Error):
        st.session_state["protect_error"] = "The vault could not save S2. Check local storage and try again."
    else:
        st.session_state.pop("protect_error", None)
        st.session_state["protect_saved"] = result.record.pair_id


def record_table(records: list[VaultRecord]) -> None:
    st.dataframe(
        [
            {
                "Image": record.display_name,
                "Pair ID": record.pair_id,
                "Processed size": f"{record.secret_width} × {record.secret_height}",
                "Created (UTC)": record.created_at,
                "Status": "Registered",
            }
            for record in records
        ],
        hide_index=True,
        width="stretch",
    )


def dashboard(workflow: AppWorkflow) -> None:
    st.markdown(
        '<div class="bv-hero"><h1>Protect the image.<br/>Distribute the trust.</h1>'
        '<p>BioVault converts a biometric image into two visual shares. Keep S1 on your device '
        'and store S2 in the local vault. Recover the binary image by combining the matching shares with XOR.</p></div>',
        unsafe_allow_html=True,
    )
    records = workflow.vault.list_records()
    count, quorum, backend = st.columns(3)
    count.metric("Registered records", len(records))
    quorum.metric("Shares required", "2 / 2")
    backend.metric("Vault storage", "SQLite")
    st.subheader("Your workspace")
    actions = (
        ("protect", "Protect Image", "Split an image into two shares."),
        ("vault", "My Vault", "Browse saved share pairs."),
        ("recover", "Reconstruction", "Recover an image with S1."),
        ("lab", "Security Lab", "Test share security."),
    )
    with st.container(key="workspace_region"):
        grid = st.grid(len(actions), min_column_width=210, gap=12, key="workspace_actions")
        for action, page, description in actions:
            grid.button(
                f"**{page}**\n\n{description}",
                key=f"workspace_{action}",
                icon=":material/arrow_forward:",
                icon_position="right",
                on_click=navigate,
                args=(page,),
                width="stretch",
                wrap=True,
            )
    st.subheader("Recent activity")
    if records:
        record_table(records[:5])
    else:
        st.info("No records yet. Start with Protect Image.")


def protect_page(workflow: AppWorkflow) -> None:
    st.title("Protect Image")
    st.caption("The threshold and size settings determine the binary image that XOR can recover.")
    settings, preview = st.columns([0.8, 1.2], gap="large")
    with settings:
        use_sample = st.toggle("Use the bundled synthetic sample", key="protect_sample", on_change=clear_protection)
        upload = st.file_uploader(
            "Image (PNG or JPEG, up to 8 MB)",
            type=["png", "jpg", "jpeg"],
            key=f"protect_upload_{st.session_state.get('protect_upload_id', 0)}",
            on_change=clear_protection,
            disabled=use_sample,
        )
        threshold = st.slider("Binarization threshold", 1, 254, 128, on_change=clear_protection)
        max_dimension = st.select_slider(
            "Maximum processed dimension",
            options=[128, 256, 384, 512, 768, 1024],
            value=512,
            on_change=clear_protection,
        )

    binary = None
    with preview:
        if use_sample or upload is not None:
            raw, filename = (SAMPLE_PATH.read_bytes(), SAMPLE_PATH.name) if use_sample else (upload.getvalue(), upload.name)
            try:
                binary = workflow.prepare(raw, filename, threshold, max_dimension)
            except UserInputError as exc:
                st.error(str(exc))
            else:
                original, processed = st.columns(2)
                original.image(raw, caption="Source preview", width="stretch")
                processed.image(binary.png, caption=f"Binary preview · {binary.width} × {binary.height}", width="stretch")

    with settings:
        if st.button("Generate shares", type="primary", disabled=binary is None, width="stretch"):
            clear_protection()
            with st.spinner("Generating the basis-matrix shares…"):
                st.session_state["protect_result"] = workflow.generate(binary, filename)
        if use_sample or upload is not None:
            st.button("Clear image and shares", on_click=clear_protect_input, width="stretch")

    result = st.session_state.get("protect_result")
    if result is None:
        return
    st.divider()
    st.subheader("Share pair")
    st.code(result.record.pair_id, language=None)
    s1, s2 = st.columns(2)
    s1.image(result.shares.share1_png, caption="S1 · Client share", width="stretch")
    s2.image(result.shares.share2_png, caption="S2 · Server share", width="stretch")
    s1.download_button(
        "Download S1 PNG",
        result.shares.share1_png,
        file_name=f"biovault_{result.record.pair_id}_S1.png",
        mime="image/png",
        on_click="ignore",
        type="primary",
        width="stretch",
    )
    saved = st.session_state.get("protect_saved") == result.record.pair_id
    if saved:
        s2.success("S2 and its metadata are saved in the vault.")
    else:
        s2.button("Save S2 to vault", on_click=save_protection, args=(workflow,), width="stretch")
        if error := st.session_state.get("protect_error"):
            s2.error(error)
    st.caption("Download S1 and save S2 before leaving this page. Keep the downloaded PNG unchanged.")


def vault_page(workflow: AppWorkflow) -> None:
    st.title("My Vault")
    records = workflow.vault.list_records()
    if not records:
        st.info("The vault is empty.")
        st.button("Protect Image", on_click=navigate, args=("Protect Image",))
        return

    record_table(records)
    by_pair = {record.pair_id: record for record in records}
    selected = st.selectbox("Inspect a record", by_pair, format_func=lambda pair_id: record_label(by_pair[pair_id]))
    record = by_pair[selected]
    scheme, share_size, threshold = st.columns(3)
    scheme.metric("Algorithm version", record.scheme_id.rsplit("@", 1)[-1])
    share_size.metric("Share dimensions", f"{record.share_width} × {record.share_height}")
    threshold.metric("Binarization threshold", record.threshold)
    st.code(f"Record ID  {record.record_id}\nScheme     {record.scheme_id}\nS2 storage {DATABASE_NAME} / server_shares", language=None)
    st.caption("Registered records have authenticated metadata. S2 integrity is checked during reconstruction.")
    st.button("Reconstruct selected record", type="primary", on_click=navigate, args=("Reconstruction", selected))


def recover_page(workflow: AppWorkflow) -> None:
    st.title("Reconstruction")
    st.caption("Use the unchanged S1 PNG from Protect Image. The selected record supplies S2.")
    records = workflow.vault.list_records()
    if not records:
        st.info("No records are available for reconstruction.")
        return
    by_pair = {record.pair_id: record for record in records}
    target = st.session_state.pop("recovery_target", None)
    if target in by_pair:
        st.session_state["recover_record"] = target
    form, detail = st.columns([1.1, 0.9], gap="large")
    with form:
        selected = st.selectbox(
            "Choose a vault record",
            by_pair,
            format_func=lambda pair_id: record_label(by_pair[pair_id]),
            key="recover_record",
            on_change=clear_recovery_input,
        )
        upload = st.file_uploader(
            "Upload S1 PNG",
            type=["png"],
            key=f"recover_share_{st.session_state.get('recover_upload_id', 0)}",
            on_change=clear_recovery,
        )
        if st.button("Reconstruct with XOR", type="primary", disabled=upload is None, width="stretch"):
            clear_recovery()
            try:
                st.session_state["last_recovery"] = workflow.recover(selected, upload.getvalue())
            except UserInputError as exc:
                st.error(f"Reconstruction blocked. {exc}")
    with detail:
        record = by_pair[selected]
        st.metric("Expected share dimensions", f"{record.share_width} × {record.share_height}")
        st.write("BioVault verifies both PNG shares and their record binding before reconstructing the binary pixels.")

    recovered = st.session_state.get("last_recovery")
    if recovered is not None and recovered.record.pair_id == selected:
        st.divider()
        st.subheader("Recovered binary image")
        st.image(recovered.image_png, width=480)
        st.download_button(
            "Download recovered PNG",
            recovered.image_png,
            file_name=f"recovered_{selected}.png",
            mime="image/png",
            on_click="ignore",
        )
        st.button("Clear recovery and S1", on_click=clear_recovery_input)


def security_page() -> None:
    st.title("Security Lab")
    st.caption("Scenarios run against a temporary vault containing the bundled synthetic image.")
    scenario = st.selectbox("Select a scenario", SCENARIOS)
    if st.button("Run scenario", type="primary"):
        with st.spinner("Running the scenario…"):
            st.session_state["lab_result"] = (scenario, run_scenario(scenario))
    latest = st.session_state.get("lab_result")
    if latest and latest[0] == scenario:
        result = latest[1]
        st.subheader("Observed result")
        st.write(result.observed)
        st.info(result.implication)
        if result.image is not None:
            st.image(result.image, caption=result.image_caption, width=480)


def evaluation_page() -> None:
    st.title("Evaluation")
    st.caption("Measure a synthetic round trip and compare the recovered pixels with the preprocessed binary image.")
    maximum = st.select_slider("Maximum sample dimension", options=[64, 128, 256, 512, 1024], value=256)
    if st.button("Run evaluation", type="primary"):
        with st.spinner("Measuring a round trip…"):
            st.session_state["evaluation_result"] = (maximum, evaluate(maximum))
    latest = st.session_state.get("evaluation_result")
    if latest and latest[0] == maximum:
        result = latest[1]
        generation, reconstruction, accuracy, errors = st.columns(4)
        generation.metric("Generation", f"{result.generation_ms:.2f} ms")
        reconstruction.metric("Reconstruction", f"{result.reconstruction_ms:.2f} ms")
        accuracy.metric("Pixel accuracy", f"{result.accuracy:.2f}%")
        errors.metric("Pixel errors", result.pixel_errors)
        width, height = result.share_dimensions
        st.table([
            {"Share": "S1", "Dimensions": f"{width} × {height}", "PNG size (bytes)": result.s1_bytes},
            {"Share": "S2", "Dimensions": f"{width} × {height}", "PNG size (bytes)": result.s2_bytes},
        ])
        st.caption(
            f"Processed image {result.processed_dimensions[0]} × {result.processed_dimensions[1]}. "
            "Generation includes encoding both PNGs. Reconstruction includes vault retrieval and integrity checks."
        )


def main() -> None:
    st.set_page_config(page_title="BioVault", page_icon="🔐", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown('<div class="bv-brand"><span class="bv-brandmark">◈</span> BIOVAULT</div>', unsafe_allow_html=True)
        page = st.radio("Workspace", PAGES, key="navigation", on_change=change_page)
        st.divider()
        st.caption("Local academic prototype · Use synthetic images")
    try:
        if page == "Security Lab":
            security_page()
        elif page == "Evaluation":
            evaluation_page()
        else:
            pages = dict(zip(PAGES, (dashboard, protect_page, vault_page, recover_page)))
            directory = Path(os.environ.get("BIOVAULT_DATA_DIR", DEFAULT_DATA_DIR)).resolve()
            pages[page](services(directory))
    except (UserInputError, VaultConfigurationError) as exc:
        st.error(str(exc))
    except (OSError, sqlite3.Error):
        st.error("Local storage is unavailable. Check the vault directory and try again.")


if __name__ == "__main__":
    main()
