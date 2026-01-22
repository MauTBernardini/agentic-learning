import os
from dotenv import load_dotenv

load_dotenv()
# Verificação de segurança (opcional, mas boa para debug)
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("A chave GOOGLE_API_KEY não foi encontrada! Verifica o ficheiro .env")


from typing import TypedDict, Annotated, List, Union
from langchain_core.messages import BaseMessage

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode
import operator

from langgraph.graph import StateGraph, END

from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference
from pydantic import BaseModel



# O Estado é apenas um dicionário tipado
class AgentState(TypedDict):
    # A lista de mensagens é acumulativa (append)
    messages: Annotated[List[BaseMessage], operator.add]


# 1. Definir ferramentas (exemplo simples)
def multiply(a: int, b: int) -> int:
    """Multiplica dois números."""
    return a * b

tools = [multiply]
tool_node = ToolNode(tools) # Nó pré-construído que sabe executar funções

# 2. Definir o Modelo com conhecimento das ferramentas
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash").bind_tools(tools)

# 3. Definir o Nó do Agente
def call_model(state: AgentState):
    messages = state['messages']
    response = model.invoke(messages)
    # Retornamos apenas o que queremos ATUALIZAR no estado
    return {"messages": [response]}


# Função que decide o próximo passo
def should_continue(state: AgentState):
    last_message = state['messages'][-1]
    
    # Se o LLM mandou chamar uma ferramenta -> vai para o nó "tools"
    if last_message.tool_calls:
        return "tools"
    
    # Se não (respondeu texto final) -> vai para o fim
    return END    



workflow = StateGraph(AgentState)

# Adicionar os nós
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Definir o ponto de entrada (onde começa a execução)
workflow.set_entry_point("agent")

# Adicionar a lógica condicional
workflow.add_conditional_edges(
    "agent",            # De onde sai? Do agente.
    should_continue,    # Quem decide? A função should_continue.
    ["tools", END]      # Quais são os destinos possíveis?
)

# Adicionar a aresta de volta (O LOOP!)
# Depois da ferramenta rodar, voltamos SEMPRE ao agente para ele ler o resultado
workflow.add_edge("tools", "agent")

# Compilar o grafo (transforma num executável)
app = workflow.compile()





api = FastAPI()

class UserInput(BaseModel):
    message: str

@api.post("/chat")
async def chat_endpoint(input: UserInput):
    inputs = {"messages": [("user", input.message)]}
    
    # Usamos ainvoke para não bloquear o servidor (lembras-te do Subtópico 3?)
    result = await app.ainvoke(inputs)
    
    # Pegamos na última mensagem (a resposta final do bot)
    final_response = result["messages"][-1].content
    return {"response": final_response}


### Scalar API Documentation
@api.get("/scalar", include_in_schema=False)
def get_scalar_docs():
    return get_scalar_api_reference(
        openapi_url=api.openapi_url,
        title="Scalar API",
    )
