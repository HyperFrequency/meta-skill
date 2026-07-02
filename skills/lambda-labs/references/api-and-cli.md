# Lambda Labs API & CLI Reference

Programmatic control of instances, SSH keys, and filesystems via the Python
client or raw `curl`. The Lambda Cloud REST API base URL is
`https://cloud.lambdalabs.com/api/v1`. Authentication accepts the API key as
HTTP basic-auth username (`-u $LAMBDA_API_KEY:`, note trailing colon) or as a
bearer token.

> The PyPI `lambda-cloud-client` (v1.0.0, API v1.4.0) is a community
> OpenAPI-generated client. For raw HTTP, prefer `curl`/`requests`.

## Python client

### Installation & authentication

```bash
pip install lambda-cloud-client
```

```python
import os
import lambda_cloud_client

configuration = lambda_cloud_client.Configuration(
    host="https://cloud.lambdalabs.com/api/v1",
    access_token=os.environ["LAMBDA_API_KEY"],
)
```

### List available instance types

```python
with lambda_cloud_client.ApiClient(configuration) as api_client:
    api = lambda_cloud_client.DefaultApi(api_client)
    types = api.instance_types()
    for name, info in types.data.items():
        print(f"{name}: {info.instance_type.description}")
```

### Launch an instance

```python
from lambda_cloud_client.models import LaunchInstanceRequest

request = LaunchInstanceRequest(
    region_name="us-west-1",
    instance_type_name="gpu_1x_h100_sxm5",
    ssh_key_names=["my-ssh-key"],
    file_system_names=["my-filesystem"],  # Optional
    name="training-job",
)
response = api.launch_instance(request)
instance_id = response.data.instance_ids[0]
print(f"Launched: {instance_id}")
```

### List running instances

```python
instances = api.list_instances()
for instance in instances.data:
    print(f"{instance.name}: {instance.ip} ({instance.status})")
```

### Terminate an instance

```python
from lambda_cloud_client.models import TerminateInstanceRequest

api.terminate_instance(TerminateInstanceRequest(instance_ids=[instance_id]))
```

### SSH key management

```python
from lambda_cloud_client.models import AddSshKeyRequest

api.add_ssh_key(AddSshKeyRequest(name="my-key", public_key="ssh-rsa AAAA..."))
keys = api.list_ssh_keys()
api.delete_ssh_key(key_id)
```

## Raw curl

### List instance types

```bash
curl -u $LAMBDA_API_KEY: \
  https://cloud.lambdalabs.com/api/v1/instance-types | jq
```

### Launch an instance

```bash
curl -u $LAMBDA_API_KEY: \
  -X POST https://cloud.lambdalabs.com/api/v1/instance-operations/launch \
  -H "Content-Type: application/json" \
  -d '{
    "region_name": "us-west-1",
    "instance_type_name": "gpu_1x_h100_sxm5",
    "ssh_key_names": ["my-key"]
  }' | jq
```

### Terminate an instance

```bash
curl -u $LAMBDA_API_KEY: \
  -X POST https://cloud.lambdalabs.com/api/v1/instance-operations/terminate \
  -H "Content-Type: application/json" \
  -d '{"instance_ids": ["<INSTANCE-ID>"]}' | jq
```

## SSH configuration

```bash
# Generate a key locally, then add the public key in the Lambda console or via API
ssh-keygen -t ed25519 -f ~/.ssh/lambda_key

# Connect (default user is ubuntu)
ssh -i ~/.ssh/lambda_key ubuntu@<INSTANCE-IP>

# Add more keys on the instance
echo 'ssh-rsa AAAA...' >> ~/.ssh/authorized_keys
ssh-import-id gh:username          # import from GitHub

# Tunnel Jupyter (8888) and TensorBoard (6006)
ssh -L 8888:localhost:8888 -L 6006:localhost:6006 ubuntu@<IP>
```

Only port 22 is open by default; open additional ports in the Lambda console.
ICMP is allowed by default.
