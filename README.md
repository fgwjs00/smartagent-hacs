# SmartAgent for Home Assistant

SmartAgent is a local-first smart home agent for Home Assistant. It helps connect devices, rooms, scenes, automations, voice interaction, and a central control screen into one coordinated home intelligence layer.

This repository provides the Home Assistant integration part of SmartAgent.

Current release: `Beta 0.0.1`

## What SmartAgent Does

- Connects Home Assistant entities to SmartAgent's device, room, and scene model.
- Provides the SmartAgent panel entry in Home Assistant.
- Helps installers and administrators configure devices, rooms, scenes, backups, patrol, and service status.
- Works with SmartAgent Core service for gateway UI, local AI capability, and central control screen support.
- Keeps control local-first for private home and project deployments.

## Who It Is For

SmartAgent is designed for:

- smart home installers
- after-sales support teams
- project administrators
- developers and technical operators

Daily household control is usually handled through the wall-mounted central control screen or configured Home Assistant dashboards.

## Install With HACS

1. Open HACS in Home Assistant.
2. Add this repository as a custom repository.
3. Select category `Integration`.
4. Install `AI SmartAgent`.
5. Restart Home Assistant.
6. Add the SmartAgent integration from Home Assistant integrations.

## Requirements

- Home Assistant compatible with this release.
- SmartAgent Core service deployed in the same project environment.
- Network access between Home Assistant and the SmartAgent Core service.

## Update

Updates are delivered through HACS. The version shown to users follows the SmartAgent public release line, starting from `Beta 0.0.1`.

## Support

For project delivery, installation, and after-sales support, use the official SmartAgent support channel provided with your deployment.
