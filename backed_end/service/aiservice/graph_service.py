from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor

from backed_end.config.api_key import OPEN_API_KEY
from backed_end.config.database import SQLITE_URL
from backed_end.service.agents.RAG_agent import get_rag_agent
from backed_end.service.agents.bilibili_agent import get_biliili_agent
from backed_end.service.agents.coder_agent import get_coder_agent
from backed_end.service.agents.document_translation_agent import get_document_translation_agent
from backed_end.service.agents.internet_agent import get_internet_agent
from backed_end.service.agents.plan_agent import get_plan_agent
from backed_end.service.agents.summary_agent import get_summary_agent
from backed_end.service.checkpointer.AsyncStartEndCheckpointer import AsyncStartEndCheckpointer


async def chat_service(question: str, thread_id: str,model:str,internet: bool, RAG: bool,email:str) -> str:
    # if RAG:
    #     handle_file(thread_id,True)

    config = {"configurable": {"thread_id": thread_id}}

    async with AsyncStartEndCheckpointer.from_conn_string(SQLITE_URL) as checkpointer:
        agents=[]
        if internet:
            internet_agent = await get_internet_agent()
            agents.append(internet_agent)
        RAG_agent = await get_rag_agent(thread_id)
        if RAG_agent:
            agents.append(RAG_agent)

        if RAG and email:
            translation_supervisor=await get_document_translation_agent(thread_id,email)
            agents.append(translation_supervisor)

        if RAG:
            summary_agent=get_summary_agent(thread_id)
            agents.append(summary_agent)

        plan_agent = get_plan_agent()
        agents.append(plan_agent)

        coder_agent=get_coder_agent()
        agents.append(coder_agent)
        bilibili_agent=get_biliili_agent()
        agents.append(bilibili_agent)
        supervisor = create_supervisor(
            agents=agents,
            model=ChatOpenAI(
                api_key=OPEN_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                model="qwen-max",
                temperature=0,
            ),
            prompt="""
                你是一个智能体管理者，你需要根据用户的问题来分配任务给不同的智能体。
                you must use agent to solve user's question.you mustn't answer the question by yourself.
                if you use an agent,you must wait for the agent to finish its work.
                if you think the question is too complex,you can use the plan_agent to divide the question into smaller tasks.
                you must use agents to complete these tasks.
                if user ask you to summary a document,you must use summary_agent to get the summary.
                you can use bilibili_agent to get video information from bilibili url
                you can use the translation monitor to finish translation task,if you use it,when you get his answer,you can return directly.
                you can use the summary_agent to get summary about an article.
                you can use the RAG_agent to answer questions based on the provided documents.
                if user want to translate his article,please call translation monitor,if user want to summary the article,please call summary_agent
                if user want to know something about article,please call rag_agent
                you can use the internet_agent to search the internet for information.
                you can use the coder_agent to write code
                you can't answer the question by yourself if you can get information from other agents.
                the information you get from the RAG agent is more reliable than the information you get from the internet agent.
                at last,you must conclude the answer and return the final answer to the user in Chinese.
                must in Chinese!
            """,
            include_agent_name='inline',
            output_mode="last_message",
            #state_schema=State,
            supervisor_name="monitor"
        ).compile(checkpointer=checkpointer)

        # yield f"data: __chat_id__:{thread_id}\n\n"

        async for event in supervisor.astream_events(
                {
                    "messages": HumanMessage(content=question),
                },
                config=config,
                stream_mode="values"
        ):
            if event["event"] == "on_chat_model_stream" and event["metadata"]["ls_model_name"]=="qwen-max":# and event["data"]["chunk"].response_metadata["model_name"]=="qwen-plus":
                for chunk in event["data"]["chunk"].content:
                    # yield f"data: {chunk}\n\n"
                    print(chunk,end="",flush=True)

        #     elif event["event"] == "on_tool_start":
        #         tool_name = event["name"]
        #         print(f"🔧 调用工具: {tool_name}")
        #
        # output = await supervisor.ainvoke(
        #     {
        #         "messages": [
        #             {
        #                 "role": "user",
        #                 "content": question
        #             }
        #         ]
        #
        #     },
        #     config=config,
        #     stream_mode="values"
        # )
        # return (output["messages"][-1].content)  # 打印最新的消息内容
        # await stream_response(question, supervisor,config)




if __name__ == "__main__":
    import asyncio

    while True:
        question = input("请输入问题：")
        if question.lower() == "exit":
            break
        thread_id = "4"
        asyncio.run(chat_service(question, thread_id,"quen-max",True, False,"873319973@qq.com"))
