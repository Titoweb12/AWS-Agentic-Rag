import streamlit as st

import agent
import rag_strict

st.set_page_config(page_title="AWS Agentic RAG")
st.title("AWS Agentic RAG")
st.caption(
    "Ask about S3, EC2, VPC, IAM, RDS, Lambda, DynamoDB, CloudFront, SQS or ELB. "
    "Answers come only from the official AWS FAQ pages."
)

st.sidebar.header("Example questions")
st.sidebar.markdown(
    "- What is S3 Object Lock?\n"
    "- How can I trigger a Lambda function when an object is uploaded to S3?\n"
    "- Quelle est la différence entre un security group et une network ACL ?\n"
    "- How do I configure an AWS Glue crawler?\n"
    "- Who won the 2018 World Cup?"
)

mode = st.radio(
    "Pipeline", ["Agent (LangGraph)", "Naive RAG (strict prompt)"], horizontal=True
)
question = st.text_input("Your question")

if st.button("Ask") and question.strip():
    q = question.strip()
    try:
        with st.spinner("Searching the documentation..."):
            if mode.startswith("Agent"):
                state = agent.app.invoke({"question": q})
                answer = state["answer"]
                passages = state.get("passages", [])
                kept = {c["id"] for c in state.get("relevant", [])}
                trace = (
                    f"Route: {state.get('route')} | Language: {state.get('language')} | "
                    f"Search query: {state.get('search_query', '-')} | "
                    f"Rewrites: {state.get('reformulations', 0)}"
                )
            else:
                answer, passages = rag_strict.answer(q)
                kept = {c["id"] for c, _ in passages}
                trace = "Naive pipeline: one rewrite, top 5 passages, generation."
    except Exception as e:
        st.error(f"Something went wrong: {type(e).__name__}: {e}")
        st.stop()

    st.markdown(answer)
    with st.expander("How this answer was produced"):
        st.caption(trace)
        if not passages:
            st.write("No passages were retrieved.")
        for c, s in passages:
            used = "used" if c["id"] in kept else "not used"
            st.markdown(
                f"**{c['id']}** | score {s:.2f} | {used}  \n"
                f"{c['question']}  \n[{c['url']}]({c['url']})"
            )