#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { ContainerPullerStack } from '../lib/container-puller-stack';
import { ContainerBuilderStack } from '../lib/container-builder-stack';

import * as fs from 'fs';

// dynamically load app-config.json
// this is an alternative to the following which works if config is static and/or
// can be commited with the code base:
// import * as config from '../app-config.json';
// this is simple for now, but if config gets more complex consider using node-config instead
const app_config = process.env.CDK_APP_CONFIG || 'app-config.json';
let source_uris: string[] = [];
try {
  const config = JSON.parse(fs.readFileSync(app_config, 'utf8'));
  source_uris = config.container_builder.source_uris;
  console.log('configuration loaded: ' + app_config)

} catch (error) {
  console.log('no configuration file provided. using defaults.')
}

const app = new cdk.App();
new ContainerPullerStack(app, 'OmxEcrHelper-ContainerPuller', {
  // this stack is region specific
  // users must deploy it on a per region basis
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEPLOY_REGION || process.env.CDK_DEFAULT_REGION 
  },

});

new ContainerBuilderStack(app, 'OmxEcrHelper-ContainerBuilder', {
  // this stack is region specific
  // users must deploy it on a per region basis
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEPLOY_REGION || process.env.CDK_DEFAULT_REGION 
  },

  // bucket names where container source bundles would come from
  source_uris: source_uris

});