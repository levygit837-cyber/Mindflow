"""Research Chain Template - Pre-configured chain for research tasks.

This template provides a standardized research workflow with steps for:
1. Query analysis and expansion
2. Information gathering from multiple sources
3. Source validation and fact-checking
4. Synthesis and summarization
5. Citation and reference generation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from mindflow_backend.chains.builders.sequential_builder import SequentialChainBuilder
from mindflow_backend.chains.base.chain import BaseChain
from mindflow_backend.chains.base.step import StepType
from mindflow_backend.chains.base.types import ChainConfig


class ResearchChain:
    """Pre-configured chain for research tasks."""
    
    def __init__(
        self,
        chain_id: str = "research_chain",
        max_sources: int = 5,
        enable_fact_checking: bool = True,
        synthesis_style: str = "comprehensive"  # comprehensive, concise, academic
    ) -> None:
        self.chain_id = chain_id
        self.max_sources = max_sources
        self.enable_fact_checking = enable_fact_checking
        self.synthesis_style = synthesis_style
        
        # Initialize the chain builder
        self.builder = SequentialChainBuilder(chain_id)
        self._setup_research_steps()
    
    def _setup_research_steps(self) -> None:
        """Setup the standard research workflow steps."""
        
        # Step 1: Query Analysis
        self.builder.add_step(
            step_id="analyze_query",
            step_function=self._analyze_research_query,
            step_type=StepType.PROCESSING,
            description="Analyze and expand the research query"
        )
        
        # Step 2: Source Identification
        self.builder.add_step(
            step_id="identify_sources",
            step_function=self._identify_research_sources,
            step_type=StepType.PROCESSING,
            description="Identify relevant research sources"
        )
        
        # Step 3: Information Gathering
        self.builder.add_step(
            step_id="gather_information",
            step_function=self._gather_information_from_sources,
            step_type=StepType.PROCESSING,
            description="Gather information from identified sources"
        )
        
        # Step 4: Source Validation (optional)
        if self.enable_fact_checking:
            self.builder.add_step(
                step_id="validate_sources",
                step_function=self._validate_and_fact_check,
                step_type=StepType.VALIDATION,
                description="Validate sources and fact-check information"
            )
        
        # Step 5: Synthesis
        self.builder.add_step(
            step_id="synthesize_findings",
            step_function=self._synthesize_research_findings,
            step_type=StepType.PROCESSING,
            description=f"Synthesize findings in {self.synthesis_style} style"
        )
        
        # Step 6: Citation Generation
        self.builder.add_step(
            step_id="generate_citations",
            step_function=self._generate_citations_and_references,
            step_type=StepType.PROCESSING,
            description="Generate citations and reference list"
        )
    
    async def _analyze_research_query(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze and expand the research query."""
        query = context.get("input", {}).get("query", "")
        
        # Extract key concepts and expand query
        concepts = self._extract_key_concepts(query)
        expanded_queries = self._generate_expanded_queries(query, concepts)
        
        # Determine research scope
        research_scope = self._determine_research_scope(query)
        
        return {
            "output": {
                "original_query": query,
                "key_concepts": concepts,
                "expanded_queries": expanded_queries,
                "research_scope": research_scope,
                "query_analysis": {
                    "complexity": self._assess_query_complexity(query),
                    "domain": self._identify_research_domain(query),
                    "time_sensitivity": self._check_time_sensitivity(query)
                }
            }
        }
    
    async def _identify_research_sources(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify relevant research sources."""
        query_analysis = context.get("input", {})
        
        # Identify source types needed
        source_types = self._determine_needed_source_types(query_analysis)
        
        # Generate potential sources
        potential_sources = []
        for source_type in source_types:
            sources = await self._find_sources_by_type(
                query_analysis, 
                source_type
            )
            potential_sources.extend(sources)
        
        # Rank and select top sources
        ranked_sources = self._rank_sources_by_relevance(
            potential_sources, 
            query_analysis
        )
        
        selected_sources = ranked_sources[:self.max_sources]
        
        return {
            "output": {
                "identified_sources": selected_sources,
                "source_types_used": source_types,
                "total_sources_found": len(potential_sources),
                "sources_selected": len(selected_sources)
            }
        }
    
    async def _gather_information_from_sources(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Gather information from identified sources."""
        sources = context.get("input", {}).get("identified_sources", [])
        query_analysis = context.get("input", {})
        
        gathered_information = []
        failed_sources = []
        
        for source in sources:
            try:
                # Extract information from source
                info = await self._extract_from_source(source, query_analysis)
                
                gathered_information.append({
                    "source": source,
                    "information": info["content"],
                    "relevance_score": info["relevance_score"],
                    "extraction_method": info["method"],
                    "timestamp": info["timestamp"],
                    "confidence": info.get("confidence", 0.8)
                })
                
            except Exception as e:
                failed_sources.append({
                    "source": source,
                    "error": str(e)
                })
        
        # Deduplicate and merge information
        merged_info = self._merge_similar_information(gathered_information)
        
        return {
            "output": {
                "gathered_information": merged_info,
                "successful_extractions": len(gathered_information),
                "failed_extractions": len(failed_sources),
                "failed_sources": failed_sources,
                "information_quality": self._assess_information_quality(merged_info)
            }
        }
    
    async def _validate_and_fact_check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate sources and perform fact-checking."""
        information = context.get("input", {}).get("gathered_information", [])
        
        validation_results = []
        fact_checks = []
        
        for info_item in information:
            # Validate source credibility
            source_validation = self._validate_source_credibility(info_item["source"])
            
            # Fact-check key claims
            claims = self._extract_key_claims(info_item["information"])
            claim_validations = []
            
            for claim in claims:
                fact_check_result = await self._fact_check_claim(claim)
                claim_validations.append({
                    "claim": claim,
                    "fact_check": fact_check_result,
                    "confidence": fact_check_result.get("confidence", 0.5)
                })
            
            validation_results.append({
                "information": info_item,
                "source_validation": source_validation,
                "claim_validations": claim_validations
            })
            
            fact_checks.extend(claim_validations)
        
        # Overall credibility assessment
        overall_credibility = self._assess_overall_credibility(validation_results)
        
        return {
            "output": {
                "validation_results": validation_results,
                "fact_checks": fact_checks,
                "overall_credibility": overall_credibility,
                "information_filtered": self._filter_low_credibility_info(
                    validation_results, overall_credibility
                )
            }
        }
    
    async def _synthesize_research_findings(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize research findings into comprehensive answer."""
        information = context.get("input", {})
        
        # Handle both cases: with and without validation
        if "validation_results" in information:
            validated_info = information["validation_results"]
            fact_checks = information["fact_checks"]
        else:
            validated_info = information.get("gathered_information", [])
            fact_checks = []
        
        # Generate synthesis based on style
        if self.synthesis_style == "comprehensive":
            synthesis = await self._generate_comprehensive_synthesis(
                validated_info, fact_checks
            )
        elif self.synthesis_style == "concise":
            synthesis = await self._generate_concise_synthesis(
                validated_info, fact_checks
            )
        elif self.synthesis_style == "academic":
            synthesis = await self._generate_academic_synthesis(
                validated_info, fact_checks
            )
        else:
            synthesis = await self._generate_default_synthesis(
                validated_info, fact_checks
            )
        
        return {
            "output": {
                "synthesis": synthesis["content"],
                "synthesis_style": self.synthesis_style,
                "key_findings": synthesis["key_findings"],
                "knowledge_gaps": synthesis["knowledge_gaps"],
                "confidence_level": synthesis["confidence"],
                "sources_utilized": len(validated_info)
            }
        }
    
    async def _generate_citations_and_references(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate proper citations and reference list."""
        synthesis = context.get("input", {})
        
        # Extract sources used in synthesis
        cited_sources = self._extract_cited_sources(synthesis)
        
        # Generate citations in different formats
        citations = {
            "apa": self._generate_apa_citations(cited_sources),
            "mla": self._generate_mla_citations(cited_sources),
            "chicago": self._generate_chicago_citations(cited_sources),
            "bibtex": self._generate_bibtex_citations(cited_sources)
        }
        
        # Generate reference list
        reference_list = self._generate_reference_list(cited_sources)
        
        return {
            "output": {
                "citations": citations,
                "reference_list": reference_list,
                "total_sources_cited": len(cited_sources),
                "citation_formats": list(citations.keys())
            }
        }
    
    def build(self) -> BaseChain:
        """Build the research chain.
        
        Returns:
            Configured SequentialChain instance
        """
        return self.builder.build()
    
    # Helper methods (simplified implementations for demonstration)
    
    def _extract_key_concepts(self, query: str) -> List[str]:
        """Extract key concepts from query."""
        # Simple keyword extraction (would use NLP in production)
        words = query.lower().split()
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        concepts = [word for word in words if len(word) > 3 and word not in stop_words]
        return list(set(concepts))
    
    def _generate_expanded_queries(self, query: str, concepts: List[str]) -> List[str]:
        """Generate expanded search queries."""
        expanded = [query]  # Include original
        for concept in concepts[:3]:  # Limit expansions
            expanded.append(f"{concept} research")
            expanded.append(f"{concept} study")
            expanded.append(f"latest {concept} findings")
        return list(set(expanded))
    
    def _determine_research_scope(self, query: str) -> str:
        """Determine the scope of research needed."""
        if any(word in query.lower() for word in ["overview", "introduction", "basics"]):
            return "general"
        elif any(word in query.lower() for word in ["detailed", "comprehensive", "in-depth"]):
            return "detailed"
        elif any(word in query.lower() for word in ["latest", "recent", "current"]):
            return "current"
        else:
            return "standard"
    
    def _assess_query_complexity(self, query: str) -> str:
        """Assess the complexity of the research query."""
        if len(query) > 200:
            return "high"
        elif len(query) > 100:
            return "medium"
        else:
            return "low"
    
    def _identify_research_domain(self, query: str) -> str:
        """Identify the research domain."""
        domain_keywords = {
            "technology": ["software", "programming", "ai", "computer", "technology"],
            "science": ["research", "study", "experiment", "analysis", "data"],
            "business": ["market", "industry", "company", "finance", "economy"],
            "health": ["medical", "health", "disease", "treatment", "medicine"]
        }
        
        query_lower = query.lower()
        for domain, keywords in domain_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return domain
        
        return "general"
    
    def _check_time_sensitivity(self, query: str) -> bool:
        """Check if the query is time-sensitive."""
        time_sensitive_words = ["latest", "recent", "current", "today", "now", "2023", "2024", "2025"]
        return any(word in query.lower() for word in time_sensitive_words)
    
    def _determine_needed_source_types(self, query_analysis: Dict[str, Any]) -> List[str]:
        """Determine what types of sources are needed."""
        domain = query_analysis.get("research_scope", {}).get("domain", "general")
        
        if domain == "technology":
            return ["academic_papers", "technical_docs", "industry_reports"]
        elif domain == "science":
            return ["academic_papers", "peer_reviewed", "research_databases"]
        elif domain == "business":
            return ["market_reports", "industry_analysis", "company_documents"]
        else:
            return ["general_web", "encyclopedia", "news_articles"]
    
    async def _find_sources_by_type(self, query_analysis: Dict[str, Any], source_type: str) -> List[Dict]:
        """Find sources of a specific type."""
        # This would integrate with actual search APIs
        # For now, return mock sources
        mock_sources = {
            "academic_papers": [
                {"type": "academic", "title": "Research Paper on AI", "url": "example.com/paper1"},
                {"type": "academic", "title": "Machine Learning Study", "url": "example.com/paper2"}
            ],
            "technical_docs": [
                {"type": "technical", "title": "API Documentation", "url": "example.com/docs"},
                {"type": "technical", "title": "Technical Guide", "url": "example.com/guide"}
            ],
            "general_web": [
                {"type": "web", "title": "Wikipedia Article", "url": "example.com/wiki"},
                {"type": "web", "title": "News Article", "url": "example.com/news"}
            ]
        }
        
        return mock_sources.get(source_type, [])
    
    def _rank_sources_by_relevance(self, sources: List[Dict], query_analysis: Dict[str, Any]) -> List[Dict]:
        """Rank sources by relevance to the query."""
        # Simple ranking based on title matching
        concepts = query_analysis.get("key_concepts", [])
        
        def relevance_score(source):
            title = source.get("title", "").lower()
            score = 0
            for concept in concepts:
                if concept in title:
                    score += 1
            return score
        
        return sorted(sources, key=relevance_score, reverse=True)
    
    async def _extract_from_source(self, source: Dict, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract information from a source."""
        # This would integrate with web scraping, API calls, etc.
        return {
            "content": f"Extracted content from {source.get('title', 'Unknown source')}",
            "relevance_score": 0.8,
            "method": "web_scraping",
            "timestamp": "2025-01-01T00:00:00Z",
            "confidence": 0.85
        }
    
    def _merge_similar_information(self, information: List[Dict]) -> List[Dict]:
        """Merge and deduplicate similar information."""
        # Simple deduplication based on content similarity
        seen_content = set()
        merged = []
        
        for info in information:
            content = info.get("information", "")
            content_hash = hash(content[:100])  # Simple hash
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                merged.append(info)
        
        return merged
    
    def _assess_information_quality(self, information: List[Dict]) -> Dict[str, Any]:
        """Assess the quality of gathered information."""
        if not information:
            return {"overall_quality": 0.0, "completeness": 0.0}
        
        avg_confidence = sum(info.get("confidence", 0) for info in information) / len(information)
        avg_relevance = sum(info.get("relevance_score", 0) for info in information) / len(information)
        
        return {
            "overall_quality": (avg_confidence + avg_relevance) / 2,
            "completeness": min(len(information) / 5.0, 1.0),  # Assume 5 sources is complete
            "source_diversity": len(set(info.get("source", {}).get("type", "") for info in information))
        }
    
    def _validate_source_credibility(self, source: Dict) -> Dict[str, Any]:
        """Validate the credibility of a source."""
        source_type = source.get("type", "")
        
        credibility_scores = {
            "academic": 0.9,
            "peer_reviewed": 0.95,
            "technical": 0.8,
            "government": 0.85,
            "news": 0.6,
            "web": 0.5
        }
        
        return {
            "credibility_score": credibility_scores.get(source_type, 0.5),
            "source_type": source_type,
            "verification_needed": source_type in ["web", "news"]
        }
    
    def _extract_key_claims(self, information: str) -> List[str]:
        """Extract key claims from information."""
        # Simple sentence extraction (would use NLP in production)
        sentences = information.split('.')
        claims = [s.strip() for s in sentences if len(s.strip()) > 20]
        return claims[:5]  # Limit to top 5 claims
    
    async def _fact_check_claim(self, claim: str) -> Dict[str, Any]:
        """Fact-check a specific claim."""
        # This would integrate with fact-checking APIs
        return {
            "claim": claim,
            "verified": True,
            "confidence": 0.8,
            "supporting_evidence": ["Evidence 1", "Evidence 2"],
            "contradictory_evidence": []
        }
    
    def _assess_overall_credibility(self, validation_results: List[Dict]) -> float:
        """Assess overall credibility of all sources."""
        if not validation_results:
            return 0.0
        
        credibility_scores = [
            result["source_validation"]["credibility_score"] 
            for result in validation_results
        ]
        
        return sum(credibility_scores) / len(credibility_scores)
    
    def _filter_low_credibility_info(self, validation_results: List[Dict], threshold: float) -> List[Dict]:
        """Filter out information from low-credibility sources."""
        return [
            result for result in validation_results
            if result["source_validation"]["credibility_score"] >= threshold
        ]
    
    async def _generate_comprehensive_synthesis(self, information: List[Dict], fact_checks: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive synthesis of findings."""
        return {
            "content": "Comprehensive synthesis of research findings with detailed analysis...",
            "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
            "knowledge_gaps": ["Gap 1", "Gap 2"],
            "confidence": 0.85
        }
    
    async def _generate_concise_synthesis(self, information: List[Dict], fact_checks: List[Dict]) -> Dict[str, Any]:
        """Generate concise synthesis of findings."""
        return {
            "content": "Concise summary of key research findings...",
            "key_findings": ["Key point 1", "Key point 2"],
            "knowledge_gaps": ["Gap 1"],
            "confidence": 0.8
        }
    
    async def _generate_academic_synthesis(self, information: List[Dict], fact_checks: List[Dict]) -> Dict[str, Any]:
        """Generate academic-style synthesis of findings."""
        return {
            "content": "Academic synthesis with formal structure and citations...",
            "key_findings": ["Academic finding 1", "Academic finding 2"],
            "knowledge_gaps": ["Research gap 1", "Research gap 2"],
            "confidence": 0.9
        }
    
    async def _generate_default_synthesis(self, information: List[Dict], fact_checks: List[Dict]) -> Dict[str, Any]:
        """Generate default synthesis of findings."""
        return await self._generate_comprehensive_synthesis(information, fact_checks)
    
    def _extract_cited_sources(self, synthesis: Dict[str, Any]) -> List[Dict]:
        """Extract sources cited in the synthesis."""
        # This would parse the synthesis to extract citations
        # For now, return mock sources
        return [
            {"title": "Source 1", "type": "academic", "url": "example.com/1"},
            {"title": "Source 2", "type": "web", "url": "example.com/2"}
        ]
    
    def _generate_apa_citations(self, sources: List[Dict]) -> List[str]:
        """Generate APA format citations."""
        return [f"Author, A. ({2024}). {source['title']}. Journal." for source in sources]
    
    def _generate_mla_citations(self, sources: List[Dict]) -> List[str]:
        """Generate MLA format citations."""
        return [f'Author. "{source["title"]}". Website, 2024.' for source in sources]
    
    def _generate_chicago_citations(self, sources: List[Dict]) -> List[str]:
        """Generate Chicago format citations."""
        return [f'Author. {source["title"]}. (2024).' for source in sources]
    
    def _generate_bibtex_citations(self, sources: List[Dict]) -> List[str]:
        """Generate BibTeX format citations."""
        return [
            f'''@article{{key,
  title={{"{source["title"]}"}},
  author={{Author}},
  year={{2024}},
}}''' for source in sources
        ]
    
    def _generate_reference_list(self, sources: List[Dict]) -> List[Dict]:
        """Generate formatted reference list."""
        return [
            {
                "number": i + 1,
                "title": source["title"],
                "authors": "Author, A.",
                "year": "2024",
                "source": source["type"],
                "url": source.get("url", "")
            }
            for i, source in enumerate(sources)
        ]
