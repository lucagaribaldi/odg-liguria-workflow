def _scrape_decreto_status_with_retries(
    self,
    deliberations: List[Dict],
    session_info: Dict,
    metrics: WorkflowMetrics,
    errors: List[str],
) -> List[Dict]:
    """
    Scrape decreto publication status with enhanced error handling and retry logic.
    
    Features:
    - Graceful degradation: Continue workflow even if scraping fails
    - Status management: Set 'Da Verificare' when scraping fails
    - Retry logic: Progressive delays (1s, 3s, 5s)
    - Batch processing: Don't block entire batch for single errors
    - Detailed reporting: Track success/failure rates
    """
    updated_deliberations = []
    scraping_delays = [1, 3, 5]  # Progressive delays in seconds
    
    self.logger.info(f"Starting decreto scraping for {len(deliberations)} deliberations with {self.max_scraping_retries} max retries")
    
    for i, deliberation in enumerate(deliberations):
        deliberation_processed = False
        numero = deliberation.get("numero", "N/A")
        
        # Initialize deliberation with default "Da Verificare" status
        deliberation["pubblicato"] = "🔍 Da verificare"
        deliberation["url_decreto"] = None
        deliberation["data_pubblicazione"] = None
        deliberation["dgr_numero"] = None
        deliberation["dgr_anno"] = None
        deliberation["scraping_attempts"] = 0
        deliberation["scraping_error"] = None
        
        self.logger.info(f"Processing deliberation {i+1}/{len(deliberations)}: numero {numero}")
        
        # Extract and validate info for scraping
        try:
            seduta = session_info.get("numero_seduta", "")
            oggetto = deliberation.get("oggetto", "")
            data_seduta = session_info.get("data_seduta", "")
            
            # Enhanced input validation
            try:
                validated_seduta = self.decreto_scraper.validate_and_sanitize_input(
                    str(seduta), "seduta", for_regex=True, max_length=50
                )
                validated_numero = self.decreto_scraper.validate_and_sanitize_input(
                    str(numero), "numero", for_regex=True, max_length=50
                )
                validated_oggetto = self.decreto_scraper.validate_and_sanitize_input(
                    oggetto, "oggetto", for_regex=False, max_length=1000
                )
            except Exception as validation_error:
                error_msg = f"Validation failed for decreto {numero}: {validation_error}"
                self.logger.error(error_msg)
                deliberation["scraping_error"] = f"Validation error: {validation_error}"
                errors.append(error_msg)
                metrics.scraping_errors.append(error_msg)
                metrics.scraping_failed += 1
                updated_deliberations.append(deliberation)
                continue
            
            # Attempt scraping with retry logic
            for attempt in range(self.max_scraping_retries + 1):  # +1 for initial attempt
                try:
                    deliberation["scraping_attempts"] = attempt + 1
                    
                    if attempt > 0:
                        delay = scraping_delays[min(attempt - 1, len(scraping_delays) - 1)]
                        self.logger.info(f"Retrying decreto {numero} (attempt {attempt + 1}/{self.max_scraping_retries + 1}) after {delay}s delay")
                        time.sleep(delay)
                        metrics.scraping_retried += 1
                    
                    # Perform scraping
                    scraping_result = self.decreto_scraper.verify_decreto_publication(
                        validated_seduta, validated_numero, validated_oggetto, data_seduta
                    )
                    
                    # Check for SSL errors specifically
                    if hasattr(self.decreto_scraper, 'ssl_failed_attempts') and self.decreto_scraper.ssl_failed_attempts > 0:
                        metrics.ssl_errors += self.decreto_scraper.ssl_failed_attempts
                        self.decreto_scraper.ssl_failed_attempts = 0  # Reset for next deliberation
                    
                    # Process successful result
                    if scraping_result.get("found"):
                        deliberation["pubblicato"] = "✅ Pubblicato"
                        deliberation["url_decreto"] = scraping_result.get("url")
                        deliberation["data_pubblicazione"] = scraping_result.get("data_pubblicazione")
                        deliberation["dgr_numero"] = scraping_result.get("dgr_numero")
                        deliberation["dgr_anno"] = scraping_result.get("dgr_anno")
                        
                        metrics.scraped_successfully += 1
                        self.logger.info(f"✅ Decreto {numero} found: {scraping_result.get('url')}")
                        
                        # Log additional details
                        if scraping_result.get("dgr_numero"):
                            self.logger.debug(f"  DGR: {scraping_result.get('dgr_numero')}/{scraping_result.get('dgr_anno', 'N/A')}")
                        if scraping_result.get("data_pubblicazione"):
                            self.logger.debug(f"  Published: {scraping_result.get('data_pubblicazione')}")
                    else:
                        # Not found, but scraping succeeded
                        deliberation["pubblicato"] = "🔍 Da verificare"
                        self.logger.info(f"🔍 Decreto {numero} not found (will remain 'Da verificare')")
                    
                    deliberation_processed = True
                    break  # Success, exit retry loop
                    
                except Exception as scraping_error:
                    error_msg = f"Scraping attempt {attempt + 1} failed for decreto {numero}: {str(scraping_error)}"
                    
                    # Check if this is an SSL error
                    if "SSL" in str(scraping_error).upper() or "CERTIFICATE" in str(scraping_error).upper():
                        metrics.ssl_errors += 1
                        self.logger.warning(f"🔒 SSL error on attempt {attempt + 1} for decreto {numero}: {scraping_error}")
                    else:
                        self.logger.warning(f"⚠️  Scraping error on attempt {attempt + 1} for decreto {numero}: {scraping_error}")
                    
                    deliberation["scraping_error"] = str(scraping_error)
                    
                    # If this is the last attempt, log as error
                    if attempt >= self.max_scraping_retries:
                        self.logger.error(f"❌ All {self.max_scraping_retries + 1} scraping attempts failed for decreto {numero}")
                        errors.append(error_msg)
                        metrics.scraping_errors.append(error_msg)
                        metrics.scraping_failed += 1
                        
            # If all attempts failed, ensure deliberation still gets added with "Da verificare" status
            if not deliberation_processed:
                self.logger.warning(f"🔍 Decreto {numero} marked as 'Da verificare' due to scraping failures")
                deliberation["pubblicato"] = "🔍 Da verificare"
                
            updated_deliberations.append(deliberation)
            
        except Exception as unexpected_error:
            # Catch-all for any unexpected errors
            error_msg = f"Unexpected error processing decreto {numero}: {str(unexpected_error)}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            metrics.errors += 1
            metrics.scraping_failed += 1
            
            # Ensure deliberation is still added with fallback status
            deliberation["pubblicato"] = "🔍 Da verificare"
            deliberation["scraping_error"] = str(unexpected_error)
            updated_deliberations.append(deliberation)
    
    # Log final scraping statistics
    total_attempted = len(deliberations)
    success_rate = (metrics.scraped_successfully / total_attempted) * 100 if total_attempted > 0 else 0
    
    self.logger.info(f"📊 Decreto scraping completed:")
    self.logger.info(f"  - Total deliberations: {total_attempted}")
    self.logger.info(f"  - Successfully scraped: {metrics.scraped_successfully}")
    self.logger.info(f"  - Failed scraping: {metrics.scraping_failed}")
    self.logger.info(f"  - Retries performed: {metrics.scraping_retried}")
    self.logger.info(f"  - SSL errors: {metrics.ssl_errors}")
    self.logger.info(f"  - Success rate: {success_rate:.1f}%")
    
    return updated_deliberations


def run_daily_verification_with_ssl_handling(self) -> Dict[str, Any]:
    """
    Run daily verification with enhanced SSL error handling.
    """
    verification_results = {
        "timestamp": datetime.now().isoformat(),
        "verified_count": 0,
        "newly_published": 0,
        "ssl_errors": 0,
        "scraping_errors": 0,
        "errors": [],
        "details": [],
    }
    
    try:
        self.logger.info("Starting daily verification with SSL error handling")
        
        # Get recent deliberations from Notion (placeholder implementation)
        recent_deliberations = self._get_unpublished_deliberations(7)  # Last 7 days
        
        if not recent_deliberations:
            self.logger.info("No unpublished deliberations found for verification")
            return verification_results
        
        self.logger.info(f"Found {len(recent_deliberations)} deliberations to verify")
        
        for deliberation in recent_deliberations:
            try:
                numero = deliberation.get("numero", "N/A")
                seduta = deliberation.get("seduta", "")
                
                # Attempt scraping with SSL error handling
                for attempt in range(self.max_scraping_retries + 1):
                    try:
                        # Validate inputs
                        validated_seduta = self.decreto_scraper.validate_and_sanitize_input(
                            str(seduta), "seduta", for_regex=True, max_length=50
                        )
                        validated_numero = self.decreto_scraper.validate_and_sanitize_input(
                            str(numero), "numero", for_regex=True, max_length=50
                        )
                        validated_oggetto = self.decreto_scraper.validate_and_sanitize_input(
                            deliberation.get("oggetto", ""), "oggetto", for_regex=False, max_length=1000
                        )
                        
                        # Perform scraping
                        scraping_result = self.decreto_scraper.verify_decreto_publication(
                            validated_seduta, validated_numero, validated_oggetto
                        )
                        
                        verification_results["verified_count"] += 1
                        
                        if scraping_result.get("found"):
                            # Update Notion with new publication status
                            self._update_notion_publication_status(deliberation, scraping_result)
                            verification_results["newly_published"] += 1
                            verification_results["details"].append({
                                "seduta": seduta,
                                "numero": numero,
                                "status": "newly_published",
                                "url": scraping_result.get("url"),
                                "attempt": attempt + 1
                            })
                            self.logger.info(f"✅ Decreto {numero} newly published: {scraping_result.get('url')}")
                        
                        break  # Success, exit retry loop
                        
                    except Exception as scraping_error:
                        if "SSL" in str(scraping_error).upper():
                            verification_results["ssl_errors"] += 1
                            self.logger.warning(f"🔒 SSL error for decreto {numero} (attempt {attempt + 1}): {scraping_error}")
                        else:
                            verification_results["scraping_errors"] += 1
                            self.logger.warning(f"⚠️  Scraping error for decreto {numero} (attempt {attempt + 1}): {scraping_error}")
                        
                        if attempt >= self.max_scraping_retries:
                            verification_results["errors"].append(f"All attempts failed for decreto {numero}: {scraping_error}")
                        else:
                            # Progressive delay before retry
                            delay = [1, 3, 5][min(attempt, 2)]
                            time.sleep(delay)
                            
            except Exception as deliberation_error:
                error_msg = f"Error processing deliberation {numero}: {str(deliberation_error)}"
                self.logger.error(error_msg)
                verification_results["errors"].append(error_msg)
        
        self.logger.info(f"Daily verification completed: {verification_results['verified_count']} verified, {verification_results['newly_published']} newly published")
        return verification_results
        
    except Exception as e:
        error_msg = f"Daily verification failed: {str(e)}"
        self.logger.error(error_msg)
        verification_results["errors"].append(error_msg)
        return verification_results